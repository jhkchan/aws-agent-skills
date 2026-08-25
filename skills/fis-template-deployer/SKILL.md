---
name: fis-template-deployer
description: 'Provisions AWS Fault Injection Simulator (FIS) experiment templates with production defaults: experiment template creation (JSON), action specification (aws:ec2:stop-instances, aws:ec2:terminate-instances, aws:ecs:drain-container-instances, aws:lambda:invoke, aws:network:disrupt-connectivity, aws:rds:failover-db-cluster, aws:s3:pause-bucket-access, aws:cloudwatch:put-metric-data), target selection via resource tags and filters, stop conditions (CloudWatch alarm auto-abort), IAM role configuration (trust policy + permissions scoped to fault actions on target resources), log group configuration, experiment start and rollback, and report generation. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a FIS experiment. Triggers: create fis experiment template, fault injection simulator, chaos experiment aws, aws:ec2:stop-instances, aws:network:disrupt- connectivity, aws:rds:failover-db-cluster, aws:ecs:drain-container- instances, fis stop condition, fis iam role, fis target tags.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with fis, ec2, ecs, rds, lambda, iam, and cloudwatch access. Works with Terraform aws_fis_experiment_template resources and CloudFormation AWS::FIS::ExperimentTemplate templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, fis, fault-injection-simulator, cloudops, deploy, chaos-engineering, experiment-template, stop-conditions, cloudwatch-alarm, iam-role, resource-tags, auto-abort
  dependencies: aws-orchestrator
  keywords: aws, fis, fault injection simulator, chaos engineering, experiment template, cloudops, deploy, stop conditions, cloudwatch alarm, iam role, resource tags, target, auto-abort, ec2 stop instances, network disrupt connectivity, rds failover, ecs drain, lambda invoke, s3 pause bucket
  when_to_use: Invoke when the user wants to create an AWS Fault Injection Simulator experiment template, configure a chaos/fault injection experiment on EC2/ECS/RDS/Lambda/S3/network resources, scope experiment targets via resource tags and filters, set stop conditions (CloudWatch alarms) for auto-abort, configure the FIS IAM role with appropriate trust and permissions, or start/rollback an experiment. Do NOT invoke for AWS Resilience Hub (readiness assessment), Chaos Mesh (EKS-native), or Gremlin (third-party chaos tool).
---

# FIS Template Deployer

An AWS CloudOps agent skill that provisions AWS Fault Injection Simulator
(FIS) experiment templates with safe production defaults. The skill walks
the operator through action specification (the eight FIS-supported fault
actions), target selection via resource tags (the safest scoping
mechanism), stop conditions (CloudWatch alarms that auto-abort the
experiment), IAM role configuration (trust policy + scoped permissions),
log group configuration, experiment start, and report generation. The
skill captures topology and fault decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create FIS experiment template, fault injection simulator, chaos
experiment AWS, aws:ec2:stop-instances, aws:network:disrupt-connectivity,
aws:rds:failover-db-cluster, aws:ecs:drain-container-instances, FIS stop
condition, FIS IAM role, FIS target tags.

## STRICT output contract

When this skill is invoked with a FIS-experiment-provisioning request
(create an experiment template, configure a fault action, scope targets,
set stop conditions, configure the IAM role, or start an experiment),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels `FIS_TEMPLATE:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Experiment template anatomy | Core structure |
| Step 2 — Actions (the eight fault types) | Fault injection |
| Step 3 — Targets (resource tags = safest scope) | Target scoping |
| Step 4 — Stop conditions (CloudWatch alarm auto-abort) | Safety guardrails |
| Step 5 — IAM role configuration | Permissions |
| Step 6 — Log group + report generation | Observability |
| Step 7 — Create, start, rollback | Provisioning step |
| Step 8 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/actions-and-targets.md | Actions + targets detail |
| references/iam-and-stop-conditions.md | IAM + stop conditions detail |

## Mindset

**One-line takeaway:** A FIS experiment template binds a fault action to
a target (scoped by resource tags) under a stop condition (a CloudWatch
alarm that auto-aborts). The IAM role must permit FIS to perform the
specific fault action on the specific target resources. Without the stop
condition, there is no safety net. Without tag-based scoping, the blast
radius is uncontrolled.

Three misconceptions dominate FIS misdesign at provisioning time:

- **"FIS runs the fault on whatever it finds."** It does not. FIS uses
  the target filter (resource tags, resource IDs, or filter patterns)
  to scope which resources the action applies to. Resource tags are the
  safest scoping mechanism because they bind to a stable, auditable
  attribute rather than an ephemeral resource ID. An underspecified
  target means an uncontrolled blast radius.

- **"FIS auto-stops when things go wrong."** It does not — unless you
  configure a stop condition. A stop condition is a CloudWatch alarm
  that, when it fires into ALARM state during the experiment, triggers
  FIS to auto-abort all running actions and roll back. Without a stop
  condition, FIS runs the action to completion regardless of impact.
  This is the #1 cause of "FIS broke production" incidents.

- **"Any IAM role works for FIS."** It does not. The FIS service role
  must trust `fis.amazonaws.com` in its trust policy AND must have
  permissions scoped to the specific fault action on the specific
  target resources. An over-permissive role (e.g., `ec2:*` on `*`)
  violates least privilege. An under-permissive role (e.g., missing
  `ec2:StopInstances`) causes the experiment to fail at start with an
  opaque permissions error.

## Configuration dependency graph (novel heuristic)

FIS experiment configurations are NOT independent. The IAM role must
permit the action on the target before the experiment can start. Stop
conditions require a CloudWatch alarm to exist before the template can
reference it. Targets must have the required tags applied before the
experiment can match them. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| CloudWatch alarm (stop condition) | metric exists; alarm configured | alarm must be in ALARM state during experiment to trigger abort; OK state does nothing | stop condition reference |
| IAM role (trust policy) | role exists; trust policy allows `fis.amazonaws.com` | service-linked role is preferred; custom role must be explicitly passed | FIS assumes the role |
| IAM role (permissions) | role has permission for the action on the target resource tags | over-permissive role violates least-privilege; under-permissive role causes experiment start failure | experiment actions execute |
| Resource tags on targets | tags applied to EC2/ECS/RDS/Lambda/S3 resources | untagged resources are NOT matched by tag-based targets — silent zero-target failure | target filter matches resources |
| Experiment template | actions, targets, stop conditions, IAM role all specified | template is immutable once created; update requires create-template-version or replace | experiment start |
| Experiment start | template exists; IAM role has permissions; targets have tags | experiment runs actions for the specified duration; auto-abort on stop condition | report generation |
| Log group | CloudWatch Logs log group exists (or FIS creates it) | without log group, experiment logs are not retained | post-experiment debugging |

**The IAM-role-permission row is the one a baseline model misses.** A
baseline says "create an experiment template." The correct heuristic
recognizes that the template's `roleArn` must allow `fis.amazonaws.com`
to assume it (trust policy) AND must grant the specific fault action's
permissions on the specific target resources (scoped permissions). The
procedure below forces an explicit decision on each.

**Cross-dependency gotchas:**
- Stop conditions reference CloudWatch alarms by ARN. The alarm must
  exist BEFORE the template is created. Creating the template first
  fails with `ResourceNotFoundException`.
- Targets with tag filters match resources at experiment START time,
  not at template CREATION time. Tagging a resource after template
  creation but before experiment start still includes it.
- The IAM role's permission boundary must allow the action on the
  target's resource tags. If the role allows `ec2:StopInstances` on
  `Resource: *` but the targets are tagged `Environment=prod`, FIS
  can still stop them — but this violates least privilege. Scope the
  role's permissions to the target tags via `Condition` blocks.
- `aws:network:disrupt-connectivity` requires the VPC and subnet
  networking permissions (the FIS network agent), not just EC2
  permissions. The role must include `ec2:CreateNetworkInterface`,
  `ec2:DeleteNetworkInterface`, and related networking actions.

## Expert heuristic: tag-based target scoping is the safest mechanism

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Expert heuristic: tag-based target scoping is the safest mechanism. See the "References (load on demand)" section.

## Expert heuristic: stop conditions auto-abort when alarms fire

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Expert heuristic: stop conditions auto-abort when alarms fire. See the "References (load on demand)" section.

## Expert heuristic: IAM role must allow the specific fault action on target resources

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Expert heuristic: IAM role must allow the specific fault action on target resources. See the "References (load on demand)" section.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| CloudWatch alarm exists (for stop condition) | Stop condition references an alarm ARN; alarm must exist first | `aws cloudwatch describe-alarms --alarm-names <name>` |
| IAM role exists with FIS trust policy | FIS assumes this role to execute fault actions | `aws iam get-role --role-name <name>` and check trust policy |
| IAM role has action-specific permissions | Role must allow the fault action on target resources | `aws iam list-attached-role-policies` and `aws iam list-role-policies` |
| Target resources tagged correctly | Tag-based targeting requires the tag to be present | `aws ec2 describe-instances --filters Name=tag:<key>,Values=<value>` |
| Log group exists (or auto-create enabled) | Experiment logs need a destination | `aws logs describe-log-groups --log-group-name-prefix /aws/fis/` |
| FIS service role (or custom role ARN) | Template references a role ARN | Confirm role ARN |
| Action parameters specified | Each action has required parameters (duration, cluster, function, etc.) | Review action spec |
| Region supports FIS | FIS is available in most regions but verify | `aws fis list-experiment-templates --region <region>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Experiment template anatomy

A FIS experiment template is a JSON document that binds actions to
targets under stop conditions, executed under an IAM role.

| Template field | Purpose | Required |
|---|---|---|
| `description` | Human-readable experiment description | Yes |
| `roleArn` | IAM role FIS assumes to execute actions | Yes |
| `actions` | Map of action name → action spec (actionId, parameters, targets) | Yes |
| `targets` | Map of target name → target spec (resourceType, resourceTags, resourceIds, filter) | Yes (if actions reference targets) |
| `stopConditions` | List of stop conditions (CloudWatch alarm ARN or source ARN) | Yes (at least one recommended) |
| `logConfiguration` | CloudWatch Logs log group for experiment output | Recommended |
| `tags` | Tag the experiment template itself | Optional |

**Minimal template structure (JSON):**

```json
{
  "description": "Stop 1 EC2 instance for 5 minutes to test HA",
  "roleArn": "arn:aws:iam::123456789012:role/FISExperimentRole",
  "actions": {
    "stop-instance": {
      "actionId": "aws:ec2:stop-instances",
      "parameters": { "startAfter": ["5m"] },
      "targets": { "Instances": "target-instances" }
    }
  },
  "targets": {
    "target-instances": {
      "resourceType": "aws:ec2:instance",
      "resourceTags": { "FIS_Target": "enabled" },
      "selectionMode": "COUNT(1)"
    }
  },
  "stopConditions": [
    { "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-CPU-High" }
  ],
  "logConfiguration": {
    "logSchemaVersion": 1,
    "cloudWatchLogsConfiguration": { "logGroup": "/aws/fis/stop-instance-experiment" }
  }
}
```

## Step 2 — Actions (the eight fault types)

FIS supports eight primary fault actions across compute, container,
network, database, storage, and observability layers.

| Action ID | Fault type | Key parameters | Impact |
|---|---|---|---|
| `aws:ec2:stop-instances` | Stop EC2 instances | `startAfter` (duration after which instances restart) | Instance stops; apps must handle restart |
| `aws:ec2:terminate-instances` | Terminate EC2 instances | `completeAfter` (duration) | Instance is terminated; ASG replacement needed |
| `aws:ecs:drain-container-instances` | Drain ECS container instances | `duration` | Tasks are moved off the instance; tests rescheduling |
| `aws:lambda:invoke` | Invoke Lambda function | `functionArn`, `functionPayload` | Invokes custom chaos/fault function |
| `aws:network:disrupt-connectivity` | Disrupt network connectivity | `duration`, `scope`, `portRanges`, `sourcePorts` | Drops/allows/delays packets between AZs/subnets |
| `aws:rds:failover-db-cluster` | Failover RDS DB cluster | N/A (uses target cluster) | Promotes a different reader to writer |
| `aws:s3:pause-bucket-access` | Pause S3 bucket access | `duration` | Bucket becomes temporarily unavailable |
| `aws:cloudwatch:put-metric-data` | Push custom metric data | `namespace`, `metricName`, `value` | Simulates a custom metric (useful for testing alarms) |

**Action duration:** most actions accept a `duration` parameter (e.g.,
`"5m"`, `"PT5M"`). The fault is applied for the duration, then FIS
rolls back (e.g., restarts stopped instances, restores bucket access).
**Action sequencing:** by default, actions in the template run
concurrently. Use the `startAfter` field to sequence actions
(e.g., `"startAfter": ["action-1"]` runs this action after action-1
completes).

## Step 3 — Targets (resource tags = safest scope)

Targets specify which resources the action applies to. Use resource
tags for the safest scoping.

| Target field | Purpose | Example |
|---|---|---|
| `resourceType` | The AWS resource type | `aws:ec2:instance`, `aws:ecs:container-instance`, `aws:rds:cluster`, `aws:lambda:function`, `aws:s3:bucket` |
| `resourceTags` | Tag key=value pairs to match | `{"FIS_Target": "enabled", "Environment": "staging"}` |
| `resourceIds` | Specific resource IDs | `["i-aaa111222", "i-bbb222333"]` |
| `filter` | Additional filter pattern | `"vpc-id = vpc-xxx"` |
| `selectionMode` | How many matched resources to target | `COUNT(1)`, `COUNT(2)`, `ALL`, `PERCENT(50)` |

**selectionMode semantics:** `COUNT(n)` targets exactly n matched
resources (chosen randomly). `ALL` targets all matched resources.
`PERCENT(n)` targets n% of matched resources (chosen randomly).

**Critical:** always use an explicit opt-in tag (e.g., `FIS_Target=enabled`)
so resources are only targeted if they are explicitly tagged. This
prevents accidental targeting of production resources.

## Step 4 — Stop conditions (CloudWatch alarm auto-abort)

Stop conditions are CloudWatch alarms that, when they fire into ALARM
state during the experiment, trigger FIS to auto-abort. **Create the
alarm BEFORE the experiment template** (stop conditions reference the
alarm ARN; if the alarm does not exist, template creation fails).

**Recommended stop condition alarms:**
- CPU utilization spike (e.g., `CPUUtilization > 90%` for 1 minute)
- Error rate spike (e.g., `5xx errors > 5%` for 1 minute)
- Latency spike (e.g., `p99 latency > 2000ms` for 1 minute)
- Health check failure (e.g., `HealthyHostCount < 1`)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "FIS-CPU-High" \
  --metric-name "CPUUtilization" --namespace "AWS/EC2" \
  --statistic "Average" --period 60 --threshold 90.0 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=AutoScalingGroupName,Value=my-asg" \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:fis-alerts" \
  --region us-east-1
```

**Critical:** without a stop condition, FIS runs the action to
completion regardless of impact. Always configure at least one.

## Step 5 — IAM role configuration

Moved verbatim to [references/iam-and-stop-conditions.md](references/iam-and-stop-conditions.md) — load on demand.
Covers: Step 5 — IAM role configuration. See the "References (load on demand)" section.

## Step 6 — Log group and report generation

FIS writes experiment state transitions and action output to a
CloudWatch Logs log group. Create the log group first, then reference it
in the template.

```bash
aws logs create-log-group \
  --log-group-name "/aws/fis/stop-instance-experiment" --region us-east-1
```

```json
"logConfiguration": {
  "logSchemaVersion": 1,
  "cloudWatchLogsConfiguration": { "logGroup": "/aws/fis/stop-instance-experiment" }
}
```

After the experiment completes (or is aborted), FIS generates a report.
Use `get-experiment` to retrieve it (key fields: state, startTime,
endTime, actions state, targets, stopConditions fired). CloudWatch Logs
Insights queries (filter `@logStream like /FIS/`) provide deeper
post-experiment analysis.

## Step 7 — Create, start, and rollback

**Create the experiment template:**

```bash
TEMPLATE_ID=$(aws fis create-experiment-template \
  --cli-input-json file://experiment-template.json \
  --region us-east-1 \
  --query 'experimentTemplate.id' --output text)
```

**Verify the template:**

```bash
aws fis get-experiment-template --id "$TEMPLATE_ID" --region us-east-1
```

**Start the experiment:**

```bash
EXPERIMENT_ID=$(aws fis start-experiment \
  --experiment-template-id "$TEMPLATE_ID" --region us-east-1 \
  --query 'experiment.id' --output text)
```

**Monitor the experiment state:** pending → running → completed |
aborted | failed.

```bash
aws fis get-experiment --id "$EXPERIMENT_ID" \
  --region us-east-1 --query 'experiment.state'
```

**Rollback:** FIS automatically rolls back actions when they complete
or when a stop condition fires (it aborts running actions, rolls back
each action — e.g., restarts stopped instances — and sets the state to
`aborted`). Manual abort: `aws fis stop-experiment --id
"$EXPERIMENT_ID"`. Verify rollback with `describe-instances` on the
target tag.

**Common mistake:** starting the experiment before the IAM role
permissions have propagated. IAM policy changes can take up to 30
seconds to propagate. Wait before starting.

## Step 8 — Recent features

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Step 8 — Recent features. See the "References (load on demand)" section.

## NEVER do these things

1. **NEVER run a FIS experiment without a stop condition.** Without a
   stop condition, FIS runs the action to completion regardless of
   impact. Always configure at least one CloudWatch alarm that
   represents "the system is degraded beyond acceptable limits."

2. **NEVER use `ALL` selection mode in production.** `ALL` targets
   every matched resource. Use `COUNT(n)` or `PERCENT(n)` to limit
   blast radius. If `ALL` is needed (e.g., full-AZ failover test),
   ensure the stop condition is aggressive and the experiment is
   carefully reviewed.

3. **NEVER target resources without an opt-in tag.** Always require
   an explicit `FIS_Target=enabled` tag (or similar). Resources
   without the tag should NEVER be matched, even if other filter
   criteria are met.

4. **NEVER use an over-permissive IAM role.** The FIS role should
   have permissions scoped to the specific fault action on the
   specific target resources (via `Condition` on resource tags).
   `ec2:*` on `*` violates least privilege.

5. **NEVER forget the IAM trust policy.** The role must trust
   `fis.amazonaws.com` in its trust policy. Without it, FIS cannot
   assume the role and the experiment fails to start.

6. **NEVER create the experiment template before the CloudWatch
   alarm.** The stop condition references the alarm ARN. If the alarm
   does not exist, template creation fails with
   `ResourceNotFoundException`.

7. **NEVER assume resource IDs are stable.** EC2 instance IDs, ECS
   task IDs, and similar change when resources are replaced (ASG,
   karpenter, spot interruption). Use resource tags for target
   stability.

8. **NEVER skip log group configuration.** Without a log group,
   experiment state changes and action output are not retained,
   making post-experiment debugging impossible.

9. **NEVER run `aws:ec2:terminate-instances` on production instances
   without an ASG.** Termination is irreversible. Without an ASG
   (or equivalent replacement mechanism), the instance is gone.
   Use `aws:ec2:stop-instances` instead for reversible faults.

10. **NEVER start an experiment before IAM permissions propagate.**
    IAM policy changes can take up to 30 seconds to propagate. Wait
    before starting the experiment to avoid opaque permission errors.

## Output format

```text
FIS_TEMPLATE: <template-id> — <action-id> on <target-description>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Action: <action-id> — <parameters>
  [✓|✗] Target: <resource-type> via <tags|IDs|filter> (selectionMode: <mode>)
  [✓|✗] Stop condition: <cloudwatch-alarm-arn>
  [✓|✗] IAM role: <role-arn> (trust: fis.amazonaws.com; permissions: <action on tags>)
  [✓|✗] Log group: <log-group-name>
  [✓|✗] Resource tags verified: <tag-key>=<value> on <n> resources
  [✓|✗] Duration: <action-duration>
  [✓|✗] Region: <region>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws fis get-experiment-template --id <template-id> --region <region>
  aws fis get-experiment --id <experiment-id> --region <region> (after start)
  aws cloudwatch describe-alarms --alarm-names <alarm-name>
```

### Worked example — EC2 stop-instances experiment with stop condition

```text
FIS_TEMPLATE: EXTVAR123456 — aws:ec2:stop-instances on EC2 instances tagged FIS_Target=enabled
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Action: aws:ec2:stop-instances — startAfter: 5m
  [✓] Target: aws:ec2:instance via tags {FIS_Target=enabled, Environment=staging} (selectionMode: COUNT(1))
  [✓] Stop condition: arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-CPU-High
  [✓] IAM role: arn:aws:iam::123456789012:role/FISExperimentRole (trust: fis.amazonaws.com; permissions: ec2:StopInstances on tag:FIS_Target=enabled)
  [✓] Log group: /aws/fis/stop-instance-experiment
  [✓] Resource tags verified: FIS_Target=enabled on 3 instances in staging
  [✓] Duration: 5m (stop, then auto-restart)
  [✓] Region: us-east-1
  [✓] Tags: Environment=staging, ExperimentType=HA-Test
VERIFICATION_COMMANDS:
  aws fis get-experiment-template --id EXTVAR123456 --region us-east-1
  aws fis get-experiment --id EXP1234567 --region us-east-1
  aws cloudwatch describe-alarms --alarm-names FIS-CPU-High
```

## Error handling

Moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.
Covers: Error handling. See the "References (load on demand)" section.

## References (load on demand)

- [references/actions-and-targets.md](references/actions-and-targets.md) — the eight fault actions and target-selection detail (existing)
- [references/iam-and-stop-conditions.md](references/iam-and-stop-conditions.md) — IAM role trust/permissions and stop-condition detail (existing); now also the full Step 5 trust/permissions policy documents and role-creation CLI
- [references/advanced-patterns.md](references/advanced-patterns.md) — expert-heuristic deep dives (tag-based target scoping, stop-condition auto-abort, IAM permission matrix) and recent AWS features (Step 8)
- [references/error-handling.md](references/error-handling.md) — error-handling deep dives: start permission denied, zero matched targets, stop condition not firing, network disruption failure, stuck in pending

## Domain

AWS CloudOps / AWS Fault Injection Simulator (FIS) Experiment Template
Provisioning & Chaos Engineering.

## AWS documentation

- **FIS User Guide** — https://docs.aws.amazon.com/fis/latest/userguide/what-is.html
- **Experiment templates** — https://docs.aws.amazon.com/fis/latest/userguide/experiment-templates.html
- **FIS actions reference** — https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html
- **FIS targets** — https://docs.aws.amazon.com/fis/latest/userguide/targets.html
- **Stop conditions** — https://docs.aws.amazon.com/fis/latest/userguide/stop-conditions.html
- **IAM role for FIS** — https://docs.aws.amazon.com/fis/latest/userguide/iam-role.html
- **AWS CLI fis** — https://docs.aws.amazon.com/cli/latest/reference/fis/
- **FIS best practices** — https://docs.aws.amazon.com/fis/latest/userguide/best-practices.html
