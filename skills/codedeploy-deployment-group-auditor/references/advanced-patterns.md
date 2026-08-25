# Advanced Patterns — CodeDeploy Deployment Group Auditor

Load-on-demand deep dives moved verbatim from SKILL.md: operator-only behaviors, edge-case catalog, deployment internals, and recent features.

## Step 0 — Expert knowledge: operator-only behaviors that change classification

These behaviors are NOT in the AWS docs and change classification if ignored.
Full details are in the Reference section at the end.

- **`enabled: true` with partial triggers is a silent misconfiguration.**
  `autoRollbackConfiguration.enabled: true` with triggers that omit
  `DEPLOYMENT_FAILURE` means rollback only fires on the listed triggers
  (e.g., alarm only). A deployment that fails via application timeout or
  instance crash — without triggering a CloudWatch alarm — will NOT
  auto-rollback. Always verify `DEPLOYMENT_FAILURE` is present in triggers.

- **`ignorePollAlarmFailure: true` disables the safety net during outages.**
  When CodeDeploy cannot reach CloudWatch (transient network, IAM permission
  gap, CloudWatch API throttle), it silently continues deploying as if all
  alarms are healthy. Infrastructure events that break CloudWatch connectivity
  are exactly when alarm monitoring is most critical. Always flag
  `ignorePollAlarmFailure: true` as a WARNING regardless of verdict.

- **AllAtATime + auto-rollback is still dangerous.** AllAtATime deploys to
  every instance simultaneously. On failure, ALL instances are down before
  rollback triggers. The rollback then re-deploys the previous revision to
  all instances. Total downtime = failure detection time + full rollback
  time. OneAtATime keeps N-1 instances healthy throughout.

- **`terminationWaitTimeInMinutes: 0` (or absent — same thing) eliminates the
  fallback fleet.** Blue/green deployment provisions a green fleet and
  terminates blue instances after success. With 0-minute wait (the API default
  when the block is omitted), blue instances are terminated immediately. A
  delayed green-fleet failure (memory leak, connection pool exhaustion
  surfacing minutes after cutover) finds the known-good blue fleet already
  gone. Recommended minimum baking window: 5 minutes.

- **OneAtATime on a single-instance deployment group is functionally
  AllAtATime.** If the deployment group targets only 1 instance (single EC2
  host via tag filter), OneAtATime deploys to that one instance — there is no
  healthy instance to maintain. CodeDeploy does not warn about this. Check
  target breadth (EC2 tags, ASG count) when the fleet is small.

- **Legacy `rollbackEnabled` vs `autoRollbackConfiguration`.** The deployment
  group API has a legacy `rollbackEnabled` boolean. The modern
  `autoRollbackConfiguration` object is authoritative. If `rollbackEnabled:
  true` is set but `autoRollbackConfiguration.enabled: false`, the legacy
  field does NOT enable proper trigger-based rollback. Always evaluate
  `autoRollbackConfiguration`.

- **`WITHOUT_TRAFFIC_CONTROL` blue/green is complexity without safety.**
  Without traffic control, CodeDeploy deregisters blue instances from the ELB
  and registers green instances — no gradual shift. Rollback requires a full
  re-deployment, not a traffic-weight flip.

## Edge-case handling

- **Partially malformed config.** If the JSON parses but individual fields are
  missing (e.g., no `autoRollbackConfiguration` block), classify what is
  present and emit a WARNING for the missing dimension. Do NOT classify the
  entire group as ERROR when only one dimension is absent — the present
  dimensions may still produce a finding.

- **ECS blue/green without explicit termination config.** ECS deployments use
  task sets behind an ELB. The `terminateBlueInstancesOnDeploymentSuccess`
  block may be absent if the deployment group was created via CloudFormation
  with default settings. If `deploymentOption` is `WITH_TRAFFIC_CONTROL` and
  termination wait is absent, assume the default of 0 minutes — flag as
  CONFIG_GAP.

- **Lambda with `CurrentVersion` and `TargetVersion` absent.** Lambda
  deployment groups without a target revision have no version to shift traffic
  to. The next deployment will fail with a validation error — flag as a
  WARNING (operational, not a config verdict driver).

- **In-place deployment with `blueGreenConfiguration` present.** If the
  deployment type is `IN_PLACE` but a `blueGreenConfiguration` block exists
  (leftover from a config change), ignore the blue/green block for
  classification — Step 4 only applies to `BLUE_GREEN` deployment type.

- **Empty deployment group (no targets).** If the deployment group has no EC2
  tag filters, no Auto Scaling groups, and no ECS service, it has no deployment
  targets. Note as a WARNING — the group is inert but not misconfigured.

## Reference — Deployment internals & non-obvious behaviors

### Deployment lifecycle and rollback mechanics

A CodeDeploy deployment progresses through phases: `Created` -> `Queued` ->
`InProgress` -> (per-instance: `Pending` -> `Installing` ->
`Succeeded`/`Failed`) -> `Succeeded`/`Failed`/`Stopped`. Auto-rollback
triggers on `DEPLOYMENT_FAILURE` when any instance transitions to `Failed`.
The rollback deployment is a **separate deployment object** that re-deploys
the last successful revision — it goes through the full lifecycle, not an
instant revert.

For blue/green with `WITH_TRAFFIC_CONTROL`, rollback is faster: CodeDeploy
shifts traffic back to the blue target group by changing listener rules,
which is near-instant compared to a full re-deployment. This is why
`WITH_TRAFFIC_CONTROL` is strongly preferred over `WITHOUT_TRAFFIC_CONTROL`.

### Non-obvious operational gotchas (senior-engineer knowledge)

These do NOT appear in the AWS CodeDeploy documentation and are learned from
production incidents. Read before classifying edge cases.

- **`DEPLOYMENT_STOP_ON_ALARM` fires only on alarm *transition* into ALARM,
  not on an ALARM state already present at deployment start.** A baseline
  alarm that is already breaching when `create-deployment` runs does NOT halt
  the deployment — CodeDeploy only reacts to OK→ALARM transitions during the
  in-progress window. Pre-existing alarm state is a silent blind spot;
  recommend operators confirm all deployment-group alarms are in OK state
  before triggering a deploy.

- **Alarm evaluation period vs. deployment window gap.** CloudWatch alarms
  need `N` consecutive datapoints in ALARM (default 1, often 2-3) before
  transitioning. A fast AllAtATime deployment can complete before the alarm
  evaluation period elapses — the breach shows up after the fleet is already
  replaced. Tune alarm `DatapointsToAlarm` to 1 for deployment-impact
  metrics, or use a dedicated high-resolution alarm during deployments.

- **Alarm polling startup blind spot.** CodeDeploy polls CloudWatch at ~60s
  intervals, but the first poll occurs *after* the first batch has already
  been deployed. For AllAtATime, the entire fleet may be deployed before the
  first alarm evaluation completes — the alarms exist but cannot prevent
  damage on fast deployments. This compounds the AllAtATime risk.

- **Alarm monitoring continues during rollback — and a broken rollback is
  unrecoverable.** When auto-rollback triggers, CodeDeploy deploys the
  previous revision while alarm monitoring continues. If the rollback itself
  triggers an alarm, CodeDeploy does NOT roll back the rollback — it marks
  the rollback deployment as failed and requires manual intervention. A
  broken previous revision combined with a broken current revision is an
  unrecoverable state without operator action.

- **`DEPLOYMENT_STOP_ON_REQUEST` is the operator-initiated rollback path.**
  When this trigger is present, calling
  `aws deploy stop-deployment --auto-rollback-allowed` triggers an automatic
  rollback. Without it, stopping a deployment does NOT trigger rollback —
  the operator must create a separate rollback deployment manually, losing
  time during an active incident.

- **Custom deployment configs are capped at 200 per region per account and
  are NOT garbage-collected.** A deployment group referencing a deleted
  custom config fails on the next deployment with
  `DeploymentConfigDoesNotExistException` — verify the referenced config
  still exists when auditing offline JSON.

- **EC2 tag-group filters are AND-ed across keys but OR-ed within a key.**
  `Key=env,Value=prod` + `Key=role,Value=web` matches instances tagged with
  BOTH (env=prod AND role=web). A common mistake is reading this as OR-across
  and producing an empty (or vastly oversized) target set. Always check
  `ec2TagSet` AND `autoScalingGroups` + `ecsServices` to confirm target
  breadth before classifying OneAtATime as safe.

- **Revision bundle type is validated at install time, not at
  `create-deployment`.** For S3-backed revisions, a mismatch between
  `s3Location.bundleType` and the actual artifact produces
  `RevisionUnsupportedFormatException` per-instance during installation —
  the deployment object is created successfully, then fails wholesale.
  Verify `targetRevision.s3Location.bundleType` matches the artifact when
  auditing rollback posture (a corrupt pin blocks rollback).

- **CloudWatch alarm names in `alarmConfiguration.alarms` are
  region-scoped to the deployment group.** Alarms in a different region (e.g.
  a multi-region dashboard alarm) silently never fire — CodeDeploy does not
  validate alarm existence at config time. Confirm each alarm name resolves
  in the deployment group's region.

### Compute platform specifics

| Platform | Deployment configs | Traffic shifting | Blue/green |
|---|---|---|---|
| Server (EC2) | OneAtATime, HalfAtATime, AllAtATime, custom | ELB deregister/register | Via Auto Scaling group replacement |
| Lambda | LambdaCanary*, LambdaLinear*, LambdaAllAtOnce | Alias traffic shifting (weighted) | Always (old vs new version) |
| ECS | ECSDefault (blue/green) | ELB target group weighting | Always (task set replacement) |

Lambda and ECS always use blue/green — there is no in-place option. The
deployment config determines how quickly traffic shifts from old to new.

### API quirks worth knowing

- `batch-get-deployment-groups` returns a slightly different shape than
  `get-deployment-group` (the batch wrapper omits `deploymentGroup` envelope
  in some CLI versions). Always normalize before classifying.
- `autoRollbackConfiguration` updates are *additive* — passing a new triggers
  list in `update-deployment-group` replaces the entire list, not appends.
  Operators frequently lose `DEPLOYMENT_STOP_ON_ALARM` this way.
- `update-deployment-group` is rate-limited to roughly 1 call/sec per
  deployment group. Burst remediation across many groups requires
  serialization, not parallel shells.

## Recent AWS features (2024-2026)

- **Blue/green deployments for ECS (2024):** CodeDeploy now supports blue/green deployments for Amazon ECS services via App Mesh or NLB traffic shifting. Auditors should verify that ECS blue/green deployment configs have appropriate termination wait times — the skill already checks this for EC2/Lambda.
- **Zonal deployment configuration (2024-2025):** CodeDeploy can now deploy one Availability Zone at a time for EC2/in-place deployments. Auditors should verify that zonal configs have appropriate rollback triggers per zone.
- **Automatic rollback enhancements (2024):** Enhanced automatic rollback with CloudWatch alarm integration improvements. No new audit-surface fields, but auditors should verify that rollback alarms cover both deployment health and application health metrics.
