# Advanced Patterns (load on demand) — Config Recorder Coverage Auditor

Expert-knowledge deep dives, edge cases, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious AWS Config behaviors (moved from SKILL.md)

These behaviors change the verdict if ignored:

- **`describe-configuration-recorders` returns config, NOT status.** A
  recorder that looks perfectly configured (allSupported: true, correct
  role) can be stopped or failing. You MUST also check
  `describe-configuration-recorder-status` for the operational truth.
  Checking only the configuration is the most common audit error.

- **`includeGlobalResourceTypes: true` in multiple regions records IAM
  changes N times.** Each region with this flag independently records the
  same IAM/CloudFront/Route 53 change. In a 20-region account, one IAM
  user creation generates 20 configuration items. AWS recommends enabling
  this in ONE region (typically us-east-1) to avoid duplicate items,
  inflated S3 costs, and forensic confusion (which region's copy is
  authoritative?). Flag regions beyond the designated global-resource
  region that have this enabled — it's a cost waste, not a coverage gap.

- **`allSupported: false` silently loses new AWS services.** When AWS
  launches a new resource type, a recorder with `allSupported: true`
  automatically includes it. A recorder with `allSupported: false` and an
  explicit resourceTypes list does NOT — the new resource type is invisible
  to Config until someone manually adds it. This is a creeping coverage
  gap that goes undetected for months.

- **Delivery channel `lastErrorCode` is the diagnostic key.** `FAILURE`
  status alone tells you delivery is broken; the error code tells you WHY:
  `NO_SUCH_BUCKET` (bucket deleted), `ACCESS_DENIED` (bucket policy missing
  the required grant to config.amazonaws.com), `INTERNAL_ERROR` (transient
  AWS-side issue). Always surface the error code in the FINDINGS.

- **Conformance packs are CloudFormation stacks under the hood.** A
  conformance pack in `CREATE_COMPLETE` or `UPDATE_COMPLETE` is effective.
  A pack in `ROLLBACK_COMPLETE` or `CREATE_FAILED` deployed zero effective
  rules — the pack name appears in the API response, but no rules are
  active. Check `DeploymentStatus`, not just existence.

- **Custom Lambda rules freeze when the Lambda is deleted.** A Config rule
  backed by a Lambda function continues to appear in `describe-config-rules`
  even after the Lambda is deleted. The rule stops evaluating compliance,
  and its last compliance result freezes indefinitely. The rule's
  `LastEvaluationTime` timestamp is the indicator — if it is stale (days/
  weeks old), the evaluation engine is dead.

- **Recording is continuous; delivery is periodic.** Config records
  configuration changes as they happen, but delivers configuration snapshots
  to S3 at the configured `deliveryFrequency` (`One_Hour`, `Three_Hours`,
  `Six_Hours`, `TwentyFour_Hours`). There is always a lag between a change
  and its appearance in S3. A `TwentyFour_Hours` frequency means up to 24
  hours of latency before a snapshot reflects the latest state.

- **Config rules quota is 150 per region by default** (adjustable via
  Service Quotas). Conformance packs deploy many rules at once — a large
  pack can push a region to the quota ceiling, silently blocking future
  rule or pack deployments. When a conformance pack is near the quota,
  flag it as a scaling risk.

- **`AWSServiceRoleForConfig` is mandatory.** The service-linked role must
  exist with the `AWSConfigRole` managed policy attached. Deleting this
  role (or detaching the policy) breaks recording with `lastStatus:
  FAILURE` — the recorder configuration looks correct but cannot function.

- **An aggregator is NOT a recorder.** A Config aggregator collects
  compliance and configuration data from source accounts/regions into a
  central account. But it does NOT record local resources — the aggregator
  account still needs its own recorder for local coverage. A region with
  only an aggregator and no local recorder has a CONFIG_GAP.

- **Rule scope can silently exclude every resource the recorder captures.**
  A Config rule has its own `Scope` (by resource type or tag). If the rule
  scope targets `AWS::EC2::Instance` but the recorder's `resourceTypes`
  list does NOT include `AWS::EC2::Instance`, the rule evaluates nothing —
  no configuration items exist for it to evaluate against. Conversely, a
  rule scope wider than the recorder scope produces silent rule inactivity
  with no error. Cross-check rule `Scope` against the recorder's recording
  group; flag rules whose target resource types are not being recorded.

- **`put-configuration-recorder` overwrites, it does not merge.** Calling
  `put-configuration-recorder` replaces the ENTIRE recorder configuration.
  A common breakage pattern: fetch the recorder, modify one field (e.g.
  flip `allSupported`), and `put` it back without preserving the existing
  `recordingGroup.resourceTypes` list — the resourceTypes array is wiped
  to empty. Always re-send the full configuration object, not a partial
  diff.

- **Organization conformance packs do NOT appear in
  `describe-conformance-packs`.** Packs deployed at the organization
  level (via the management account, CloudFormation StackSets, or
  `put-organization-conformance-pack`) are visible only through
  `describe-organization-conformance-packs` and
  `describe-organization-conformance-pack-status`. An audit that checks
  only `describe-conformance-packs` in a member account will falsely
  report zero conformance packs even when org-level packs are active and
  enforcing rules in that account.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **New resource types for recording (2024-2025):** AWS Config now supports recording for many additional resource types (S3 directory buckets, VPC Lattice resources, Clean Rooms, Bedrock resources). Auditors should verify that `allSupported=true` is set to automatically capture new resource types, or manually add newly relevant types to the recording scope.
- **Config conformance pack updates (2024):** New sample conformance packs for compliance frameworks. Auditors should verify that deployed conformance packs match the organization's active compliance requirements and are not stale.
- **Organization config aggregator enhancements:** Improved multi-account aggregation with better error reporting. Auditors should verify that the aggregator includes all organization accounts and that authorization errors are resolved.
- **Config rule evaluation frequency:** Enhanced support for periodic evaluation intervals. Auditors should verify that critical rules use appropriate evaluation frequency — over-triggered periodic rules consume Lambda budget, while under-triggered rules miss configuration drift.
