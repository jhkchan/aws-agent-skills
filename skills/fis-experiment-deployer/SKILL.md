---
name: fis-experiment-deployer
description: >-
  Provisions AWS Fault Injection Service (FIS) experiment templates with
  production-safe defaults: action targets (resource tags, ARNs, filters),
  fault actions across EC2 (stop-instances, send-api-error, terminate-
  instances), ECS (stop-task), network (blackhole, latency, loss via SSM
  on EC2/ECS ENIs), RDS (failover-db-cluster for Aurora), and Lambda
  (invoke-async), CloudWatch alarm-based stop conditions, IAM execution
  role with the FIS trust policy + least-privilege action scopes,
  experiment logging to S3 and CloudWatch Logs, and the latest primitives
  (Aurora failover, EKS pod disruption via SSM, network blackhole/
  latency/loss). Emits a READY_TO_DEPLOY / PREREQUISITES_MISSING plan
  with verified targets, actions, stop conditions, and copy-pasteable
  fis + cloudwatch commands. Use when provisioning chaos/fault
  injection experiments for game days, DR drills, resilience validation,
  or pre-prod gate checks. Triggers: FIS, fault injection, chaos
  engineering, experiment template, stop condition, Aurora failover,
  EKS pod kill, network blackhole, game day.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Live provisioning uses AWS CLI v2 with fis
  (create-experiment-template, get-experiment-template, start-experiment),
  iam (create-role, put-role-policy), cloudwatch (describe-alarms),
  s3 (create-bucket, put-bucket-policy) and logs (create-log-group).
  Works with Terraform aws_fis_experiment_template /
  aws_iam_role and CloudFormation AWS::FIS::ExperimentTemplate.
keywords:
- aws
- fis
- fault injection
- chaos engineering
- experiment template
- stop condition
- alarm-based stop
- aurora failover
- rds failover
- eks pod disruption
- ecs stop-task
- ec2 stop-instances
- ec2 send-api-error
- network blackhole
- network latency
- network loss
- lambda invoke-async
- game day
- resilience validation
- cloudops
- deploy
tags:
- aws
- fis
- fault-injection
- chaos-engineering
- experiment-template
- stop-condition
- aurora-failover
- eks-disruption
- deploy
- management
dependencies:
- aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: >-
    Provisioning an FIS experiment template for a game day, DR drill,
    or resilience gate; configuring CloudWatch alarms as stop conditions;
    scoping IAM permissions for FIS to run a specific action against a
    specific target; setting up Aurora failover, EKS pod disruption,
    ECS task stop, EC2 API error injection, network blackhole/latency/loss,
    or Lambda async invocation experiments; or wiring experiment logging
    to S3 and CloudWatch Logs. Do NOT invoke for production traffic
    reversal, incident command, or post-incident RCA — use the
    appropriate troubleshoot or operate skill.
  activation_triggers:
  - FIS experiment template
  - fault injection experiment
  - chaos engineering
  - game day drill
  - resilience validation
  - Aurora failover test
  - RDS failover experiment
  - EKS pod disruption
  - ECS stop task experiment
  - EC2 stop instances experiment
  - EC2 send API error
  - network blackhole experiment
  - network latency injection
  - network packet loss
  - Lambda invoke async experiment
  - FIS stop condition
  - alarm-based stop
  invocation_schema: >-
    Input: either (a) an experiment spec including target resource tags/
    ARNs/filters, one or more fault actions with parameters, optional
    CloudWatch alarm stop conditions, optional logging config, and
    budgetDuration; or (b) a partial spec for interactive refinement
    (e.g., "FIS experiment to fail over an Aurora cluster"). Output: a
    deterministic EXPERIMENT_TEMPLATE / VERDICT / CHECKLIST /
    VERIFICATION_COMMANDS block per the STRICT output contract, where
    VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.
---

# FIS Experiment Deployer

## What this skill does

Provisions AWS Fault Injection Service (FIS) experiment templates with
correct production-safe defaults: a least-privilege IAM execution role,
alarm-based stop conditions, target scoping via tags/ARNs/filters,
action parameters tuned to the fault type, and experiment logging. The
skill walks an 8-step procedure, surfaces the silent-failure modes
unique to FIS (most dangerous: an alarm with insufficient permissions
silently never fires as a stop condition, so an out-of-control
experiment runs to budget with no automatic halt), and emits a
READY_TO_DEPLOY checklist verifying every action, target, and stop
condition against the IAM and CloudWatch state. The single most common
incident this skill prevents: an operator points `aws:ec2:stop-instances`
at a broad tag selector (`env=prod`), with no stop condition, in an
account where the FIS role has permission to stop every EC2 instance —
the experiment stops an entire production fleet because the resource
filter was permissive.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (8 steps), verdict thresholds, action matrix | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 8-step order matters; blast-radius model | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "experiment didn't run as expected" |
| **Expert heuristic** | Target scoping myth; stop-condition silent no-op; budgetDuration | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **8-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent production outage / data-plane bugs | Review before deploy |
| **STRICT output contract** | Required EXPERIMENT_TEMPLATE / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | Aurora failover, EKS disruption, network fault actions | Stay current |

## Quick reference — provisioning summary (8 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm experiment intent + blast radius | — | wrong intent = wrong fault |
| 2 | Scope targets via tags / ARNs / filters | Yes (template only) | permissive target = production outage |
| 3 | Choose fault action(s) + parameters | Yes | wrong action = wrong fault |
| 4 | Configure stop conditions (CloudWatch alarms) | Yes | missing/no-permission = no auto-halt |
| 5 | Create IAM execution role with least privilege | Yes | over-scoped role = blast-radius multiplier |
| 6 | Configure experiment logging (S3 / CloudWatch Logs) | Yes | no logging = no post-experiment evidence |
| 7 | Set budgetDuration + (optional) schedule | Yes | long budget = long exposure |
| 8 | Verify via `get-experiment-template` + emit checklist | — | silent no-ops |

**Critical ordering constraints:** targets scoped before actions (the
target filter determines blast radius; an action chosen first invites
"point this at everything"); stop conditions resolved before IAM role
creation (the role needs `cloudwatch:DescribeAlarms` for stop-condition
alarms); IAM role scoped to the exact actions + targets before template
creation (over-scoped role persists even after the experiment); logging
configured before the experiment starts (FIS does not back-fill logs);
budgetDuration set explicitly per action (the default is the action's
natural duration, which may be longer than your maintenance window).
Rationale and the silent-failure table are below.

## Activation keywords

FIS experiment template, fault injection experiment, chaos engineering,
game day drill, resilience validation, Aurora failover test, RDS
failover experiment, EKS pod disruption, ECS stop-task experiment, EC2
stop-instances experiment, EC2 send-api-error, EC2 terminate-instances,
network blackhole experiment, network latency injection, network packet
loss, Lambda invoke-async experiment, FIS stop condition, alarm-based
stop, FIS IAM role, FIS budgetDuration.

## Invocation contract (hard requirement)

When this skill is invoked with an FIS experiment provisioning request,
the agent MUST respond with the checklist defined in §"STRICT output
contract" using the literal all-caps labels `EXPERIMENT_TEMPLATE:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
with prose, headings, or disclaimers — emit the block as the first
lines of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Reasoning framework (why the provisioning order matters)

FIS looks like "pick a fault and a target" but the underlying model has
four traps:

1. **A fault action is a payload; the target filter is the blast
   radius.** Operators focus on the action (`aws:ec2:stop-instances`)
   and treat the target as boilerplate. The action does exactly what it
   says; the target filter decides which resources it does it to. A
   broad filter (`resourceTags: env=prod`) on a stop action with no
   stop condition is a production outage waiting for the next
   `start-experiment`.

2. **Stop conditions are CloudWatch alarms — and the FIS role must have
   permission to describe them.** A stop condition is an alarm ARN that
   FIS evaluates continuously during the experiment. If the alarm goes
   ALARM, FIS halts the experiment. But FIS needs `cloudwatch:Describe-
   Alarms` on the alarm ARN; without it, the alarm state is invisible
   to FIS and the experiment runs to budget regardless. This is a
   silent no-op — the alarm exists, the stop condition is configured,
   the role lacks the permission, and there is no error.

3. **The FIS execution role is NOT the caller's role.** FIS assumes a
   role you provide when it runs the experiment. That role's policy
   determines what FIS can do — `ec2:StopInstances` on which instances,
   `rds:FailoverDBCluster` on which clusters, and so on. The caller
   being a full admin does NOT narrow the FIS role's permissions; the
   FIS role is the only thing that matters at experiment time.

4. **`budgetDuration` bounds the experiment but does NOT bound each
   action's effect.** A 5-minute budget on an EC2 stop-instances action
   means FIS will stop instances and then, after the budget, attempt
   the action's rollback (typically start-instances). But if the
   rollback fails (network partition, IAM drift), the instances stay
   stopped. The budget is a timeout, not a guarantee of recovery.

The procedure below sequences the steps to surface these traps.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing useful) | Enables downstream |
|---|---|---|---|
| Experiment template | target, action, role ARN | **template with permissive target filter = production outage on first start-experiment** | chaos drill |
| Target (resourceTags) | tag exists on at least one resource | **tags matching many resources silently expands blast radius** | scoped fault |
| Target (resourceArns) | ARNs resolvable | **stale ARN silently targets wrong resource after recreation** | precise fault |
| Target (filters) | filter syntax valid | **empty filter result = experiment runs against zero resources (success, no-op)** | filtered fault |
| Stop condition (alarm) | alarm in ALARM/OK/INSUFFICIENT_DATA | **alarm exists but role lacks cloudwatch:DescribeAlarms = stop condition silently inactive** | auto-halt |
| IAM role (FIS trust) | `Service: fis.amazonaws.com` | **wrong trust principal = experiment fails at start with AccessDenied** | FIS execution |
| IAM role (action scope) | permissions for every action's API | **missing ec2:StopInstances = action marked FAILED but experiment continues other actions** | scoped execution |
| Logging (S3) | bucket exists + fis-acct write | **bucket policy missing fis delivery grant = logs never arrive, no error** | post-experiment evidence |
| Logging (CloudWatch Logs) | log group exists | **log group deleted = no log streams, no error** | post-experiment evidence |
| Aurora failover action | cluster in AVAILABLE | **cluster already failing over = action fails with ConflictException** | DR drill |
| Network actions (SSM) | SSM agent running on target | **SSM agent offline = command never executes, no error, action "succeeds"** | network chaos |
| EKS pod disruption | SSM on worker node + kubeconfig | **SSM command runs but kubectl fails silently = no pods disrupted** | pod-level chaos |

**The four most dangerous silent-failure rows** are permissive-target,
stop-condition-without-permission, network-action-SSM-offline, and
EKS-pod-disruption-kubectl-fail. All return success on apply or even
on experiment start; the failure surfaces only when traffic doesn't
behave as expected. Step 2 (target scoping), Step 4 (stop-condition
alarm verify), Step 5 (IAM permission map), and Step 8
(`get-experiment-template` + per-action dry-run on one resource) are
non-negotiable for any production-adjacent experiment.

## Expert heuristic: the permissive-target myth

The most common misconception: "the FIS action determines what gets
disrupted." It does not, by itself, decide the scope.

```text
Operator thinks:                  What actually happens:
"aws:ec2:stop-instances action    FIS stops every instance matching
on the template" -> safe,         the target filter. If the filter is
action-level scope.               resourceTags env=prod, that is
                                  every production instance. There is
                                  no action-level scoping in FIS; the
                                  target is the scope.
```

Target scoping is a deterministic resolution at experiment start: FIS
lists all resources matching the filter and applies the action to
each. With no stop condition, the experiment runs to budget. With an
over-scoped IAM role (`ec2:StopInstances: *`), there is no second line
of defense.

This applies equally to ECS, RDS, Aurora, Lambda, and network actions:
the target filter is the blast radius. The remedy is one tag reserved
for FIS targeting (e.g., `fis-target=true`), applied only to drill
resources, plus an IAM role scoped to that tag on every action.

## Expert heuristic: stop-condition silent no-op

A stop condition is an alarm ARN. FIS polls the alarm state during the
experiment and halts when it goes ALARM. The trap: FIS needs
`cloudwatch:DescribeAlarms` permission in its execution role for those
specific alarm ARNs. Without the permission, FIS cannot read the alarm
state — and it fails open (continues the experiment) rather than
aborting on the permission gap. There is no error and no log line that
says "stop condition disabled."

**Three invariants before any production-adjacent experiment:**

1. **The alarm exists and is monitored.** `aws cloudwatch describe-
   alarms --alarm-names <name>` returns the alarm.
2. **The FIS role has `cloudwatch:DescribeAlarms` on the alarm ARN.**
   Inspect the role policy; do not assume.
3. **A manual ALARM trigger halts a dry-run experiment.** Set the alarm
   to ALARM state (force-metric) and start a 60-second experiment; the
   experiment should halt within the polling interval.

## Expert heuristic: budgetDuration vs. action natural duration

`budgetDuration` is the upper bound on the experiment. It is NOT the
duration of the fault's effect. Each FIS action has its own model:

- `aws:ec2:stop-instances`: stops instances, then (on experiment end)
  attempts to start them. The instances are STOPPED for ~(budget -
  action-duration) minutes. If start fails, they stay stopped.
- `aws:ec2:send-api-error`: returns the configured error code for API
  calls made by the target IAM role for the duration. Effect ends when
  the action ends.
- `aws:ecs:stop-task`: stops the task. ECS reschedules per the service.
  No rollback — the task stays stopped and a new one starts (or
  doesn't, depending on deployment min/ideal).
- `aws:rds:failover-db-cluster`: triggers a failover; the failover
  itself takes 30-120 seconds. No rollback — the cluster stays
  promoted until the next failover.
- `aws:network:disrupt-connectivity` (SSM-based): injects iptables/tc
  rules; on action end, SSM removes them. If SSM agent is unreachable
  at end, the rules persist.
- `aws:lambda:invoke-async`: invokes the function with the payload,
  once or N times. Effect ends when invocation completes.

**Practical default:** set `budgetDuration` to 2x the action's
expected effect duration. A 1-minute stop-instances drill gets a
2-minute budget. A 5-minute network blackhole gets a 10-minute budget.
This bounds the failure-domain if rollback fails.

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Caller IAM | `fis:CreateExperimentTemplate`, `iam:CreateRole`, `iam:PassRole` required | `aws sts get-caller-identity` + IAM policy check |
| Target resources exist | Empty target = silent no-op experiment | `aws ec2 describe-instances --filters Name=tag:<k>,Values=<v>` |
| Target tag is reserved for FIS | Permissive tag (`env=prod`) = production outage | Confirm tag value population; prefer `fis-target=true` |
| CloudWatch alarm exists (stop condition) | Stop condition ARN must be resolvable | `aws cloudwatch describe-alarms --alarm-names <name>` |
| Alarm not in INSUFFICIENT_DATA | Stop condition silently inactive if no data | `aws cloudwatch describe-alarms --alarm-names <name> --query 'MetricAlarms[0].StateValue'` |
| SSM agent reachable (network actions) | Network actions run via SSM; offline agent = no-op | `aws ssm describe-instance-information --filters Name=InstanceIds,Values=<id>` |
| Aurora cluster AVAILABLE (failover) | Cluster mid-failover = action fails | `aws rds describe-db-clusters --db-cluster-identifier <id>` |
| EKS worker node has SSM + kubectl (EKS disruption) | SSM command runs but kubectl fails silently otherwise | `aws ssm describe-instance-information` + `aws eks describe-cluster` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 8-step provisioning procedure

### Step 1 — Confirm experiment intent + blast radius

Before any resource lookup, name the intent in one sentence: "drain
10% of an ASG for 60 seconds to test alerting," "fail over Aurora
cluster X to validate RTO," "blackhole traffic from app-A to db-B for
5 minutes." The intent drives the target filter, the action, and the
stop condition. If the intent is "see what breaks," the verdict is
PREREQUISITES_MISSING — FIS is not a discovery tool.

### Step 2 — Scope targets via tags / ARNs / filters

| Target type | When to use | Verification |
|---|---|---|
| `resourceTags` | Drills across a labeled group (e.g., fis-target=true) | `aws ec2 describe-instances --filters` |
| `resourceArns` | Precise single-resource faults | resource ARN resolvable |
| `filters` (resource type + boolean) | Complex scoping (e.g., instances in ASG X with tag Y) | List + count before template |

**Common mistake:** using `env=prod` or `service=critical` as a target
tag. Always prefer a tag whose only population is FIS-eligible
resources (`fis-target=true`). Confirm the population size before
applying the template — a 1000-instance match on a stop action is a
fleet-wide outage.

### Step 3 — Choose fault action(s) + parameters

| Action ID | Effect | Key parameters | Natural duration |
|---|---|---|---|
| `aws:ec2:stop-instances` | Stops the matched EC2 instances | duration (PTxS) | stops, then starts at action end |
| `aws:ec2:send-api-error` | Returns error for IAM-role API calls | errorCode (ThrottlingException, etc.), service, duration | effect ends with action |
| `aws:ec2:terminate-instances` | Terminates matched EC2 instances | (none — irreversible) | irreversible |
| `aws:ecs:stop-task` | Stops matched ECS tasks | (none) | task stopped, ECS reschedules |
| `aws:eks:pod-cleanup` (SSM) | Deletes pods via kubectl on worker node | kubectl command via SSM | pods deleted, controller reschedules |
| `aws:network:disrupt-connectivity` (SSM) | Network blackhole/latency/loss via tc | networkInterfaces, disruptionType, duration | rules persist if SSM offline at end |
| `aws:rds:failover-db-cluster` | Promotes a different Aurora writer | (none) | 30-120s failover |
| `aws:lambda:invoke-async` | Invokes Lambda with payload asynchronously | function ARN, payload | invocation completes |

**Common mistake:** using `terminate-instances` for a chaos drill when
you meant `stop-instances`. Terminate is irreversible — the ASG will
provision replacements, but state is lost. Always use stop for
stateful drills.

### Step 4 — Configure stop conditions (CloudWatch alarms)

A stop condition is an array of CloudWatch alarm ARNs. FIS evaluates
them continuously; any alarm going ALARM halts the experiment.

```bash
aws cloudwatch describe-alarms --alarm-names <ALARM_NAME> \
  --query 'MetricAlarms[0].{Name:AlarmName,State:StateValue,Arn:AlarmArn}' \
  --output json
```

Confirm:
1. The alarm exists (a typo'd name = silent no-op stop condition).
2. The alarm is in OK or ALARM state (not INSUFFICIENT_DATA — that
   means it will never fire as a stop condition).
3. The FIS role has `cloudwatch:DescribeAlarms` on the alarm ARN.

### Step 5 — Create IAM execution role with least privilege

**Trust policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "fis.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Permission policy (least privilege):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:StopInstances", "ec2:StartInstances"],
      "Resource": "*",
      "Condition": {"StringEquals": {"aws:ResourceTag/fis-target": "true"}}
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:DescribeAlarms"],
      "Resource": "arn:aws:cloudwatch:<region>:<account>:alarm:<ALARM_NAME>"
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:SendCommand", "ssm:GetCommandInvocation"],
      "Resource": ["arn:aws:ssm:<region>::document/AWS-RunShellScript",
                   "arn:aws:ec2:<region>:<account>:instance/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:<region>:<account>:log-group:/aws/fis/<exp>:*"
    }
  ]
}
```

**Common mistake:** granting `ec2:StopInstances` on `Resource: "*"`
without the tag condition. The condition is the second line of
defense — if the target filter is misconfigured, the IAM condition
still blocks the action on non-FIS resources.

### Step 6 — Configure experiment logging (S3 / CloudWatch Logs)

**S3 logging:**
```json
"logConfiguration": {
  "logSchemaVersion": 2,
  "cloudWatchLogsConfiguration": {"logGroupArn": "arn:aws:logs:<region>:<account>:log-group:/aws/fis/<exp>"},
  "s3Configuration": {"bucketName": "fis-experiment-logs-<account>", "prefix": "experiments/<exp>/"},
  "logsSchemaVersion": 2
}
```

The S3 bucket MUST grant `s3:PutObject` to the FIS service principal
(`service-role/fis.amazonaws.com` or the FIS logging account). The
CloudWatch log group MUST exist before the experiment starts.

**Common mistake:** referencing a log group that does not exist. FIS
does not create it; logging silently fails.

### Step 7 — Set budgetDuration + (optional) schedule

```json
"budgetDuration": "PT5M"
```

Set 2x the action's expected effect duration. For multi-action
experiments, the budget bounds the total — set it to the sum of
sequential action durations plus 50% margin.

For scheduled game days, use a CloudWatch Events rule that invokes
`fis:start-experiment` at the scheduled time. Do NOT leave an
auto-start rule armed in production — disarm between drills.

### Step 8 — Verify via `get-experiment-template` + emit checklist

```bash
aws fis get-experiment-template --id <TEMPLATE_ID>

# Optional: dry-run by starting the experiment and aborting within 30s
# aws fis start-experiment --experiment-template-id <TEMPLATE_ID>
# aws fis stop-experiment --id <EXPERIMENT_ID>
```

Confirm every action ID, every target filter, every stop condition
alarm ARN, and the IAM role ARN are present in the stored template.
FIS does not validate IAM permissions at template creation time — only
at experiment start, where the first action fails with AccessDenied.

## NEVER do these things

These anti-patterns cause production outages, data-plane bugs, or
silent no-ops. Each is observed in real production incidents.

1. **NEVER scope an FIS target with a broad production tag
   (`env=prod`, `service=critical`).** Why it's wrong: the target
   filter IS the blast radius. A stop action against `env=prod` stops
   every matching instance. Use a tag reserved for FIS
   (`fis-target=true`), and scope the IAM role with the same tag as a
   second line of defense.

2. **NEVER deploy an experiment template without at least one stop
   condition.** Why it's wrong: without an alarm, an out-of-control
   experiment runs to budgetDuration with no automatic halt. Even for
   "safe" drills, configure at least an "error rate above threshold"
   alarm. A no-stop-condition experiment is a manual kill or wait-
   for-budget experiment.

3. **NEVER grant the FIS execution role `Resource: "*"` on the action
   APIs without tag conditions.** Why it's wrong: the role is the
   ONLY thing that scopes the experiment at runtime. An admin caller
   with a permissive FIS role still produces a fleet-wide outage. The
   tag condition is the second line of defense when the target filter
   is wrong.

4. **NEVER assume a stop condition will fire without verifying
   `cloudwatch:DescribeAlarms` on the alarm ARN in the FIS role.** Why
   it's wrong: FIS fails open on missing alarm permission — the
   experiment runs to budget with the stop condition silently
   inactive. Verify by reading the role policy and by force-triggering
   the alarm in a dry run.

5. **NEVER use `aws:ec2:terminate-instances` when you mean
   `stop-instances`.** Why it's wrong: terminate is irreversible. The
   ASG provisions replacements, but instance state and ephemeral disks
   are gone. For chaos drills where the workload should recover, use
   stop-instances. Reserve terminate-instances for tests of stateless
   auto-replacement, never stateful services.

## Output format

```
EXPERIMENT_TEMPLATE: <name> (action: <action-id>, target: <target-summary>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Intent + blast radius: <one-sentence intent>, blast radius <count> <type>
  [✓|✗] Target scoped: <resourceTags|resourceArns|filters> (<count> resources)
  [✓|✗] Action(s): <action-id list> (parameters: <key params>)
  [✓|✗] Stop condition(s): <alarm-name list> (state: OK|ALARM)
  [✓|✗] IAM role: <role-name> (fis trust, least-privilege actions, tag conditions)
  [✓|✗] Logging: S3 <bucket> + CloudWatch Logs <log-group>
  [✓|✗] budgetDuration: <PTxM> (rationale: <action-appropriate>)
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
EXPERIMENT_TEMPLATE: <name> (action: <action-id>, target: <target-summary>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Intent + blast radius: <one-sentence intent>, blast radius <count> <type>
  [✓|✗] Target scoped: <resourceTags|resourceArns|filters> (<count> resources)
  [✓|✗] Action(s): <action-id list> (parameters: <key params>)
  [✓|✗] Stop condition(s): <alarm-name list> (state: OK|ALARM)
  [✓|✗] IAM role: <role-name> (fis trust, least-privilege actions, tag conditions)
  [✓|✗] Logging: S3 <bucket> + CloudWatch Logs <log-group>
  [✓|✗] budgetDuration: <PTxM> (rationale: <action-appropriate>)
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 7
   checklist items.** Every item MUST appear with a status marker:
   `[✓]`, `[✗]`, or `[OPTIONAL]`. Omitting a row implies it was not
   evaluated.

2. **NEVER mark Target scoped `[✓] resourceTags` without citing the
   resource count.** A permissive tag is the leading cause of FIS
   outages. The checklist MUST cite the resolved count
   (e.g., "3 instances") or mark the item `[✗]` with a warning.

3. **NEVER mark Stop condition(s) `[✓]` without confirming the alarm
   state is OK or ALARM (not INSUFFICIENT_DATA) AND the FIS role has
   `cloudwatch:DescribeAlarms` on the ARN.** Both checks are required;
   either missing means the stop condition is silently inactive. The
   checklist MUST cite the alarm state and the role's alarm permission.

4. **NEVER mark IAM role `[✓]` without citing that the action
   permissions carry tag conditions** (e.g.,
   `aws:ResourceTag/fis-target=true`). Without the condition, the role
   is the only line of defense — and over-scoped roles are the second-
   most-common FIS incident.

5. **NEVER mark budgetDuration `[✓]` without a one-line rationale
   tied to the action.** A 30-minute budget on a stop-instances drill
   is 30 minutes of stopped production; a 30-second budget on a
   network blackhole may be too short for the SSM command to land.
   The checklist MUST include the rationale.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] Stop condition: alarm fis-stop-rate not found — create alarm
   before applying`. A bare `[✗]` is non-compliant.

7. **NEVER include `aws:ec2:terminate-instances` in an action list
   without a `[WARN]` note in the checklist.** Terminate is
   irreversible. The checklist MUST cite that stateful resources will
   be lost.

### Perfect example output — READY_TO_DEPLOY

```text
EXPERIMENT_TEMPLATE: ec2-stop-canary (action: aws:ec2:stop-instances, target: fis-target=true)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Intent + blast radius: Stop one canary instance for 60s to validate auto-recovery, blast radius 1 instance
  [✓] Target scoped: resourceTags fis-target=true (1 instance i-0abc123)
  [✓] Action(s): aws:ec2:stop-instances (duration PT60S)
  [✓] Stop condition(s): fis-stop-error-rate (state: OK)
  [✓] IAM role: fis-execution-role (fis trust, ec2:StopInstances + StartInstances scoped to aws:ResourceTag/fis-target=true, cloudwatch:DescribeAlarms on fis-stop-error-rate)
  [✓] Logging: S3 fis-logs-111111111111 + CloudWatch Logs /aws/fis/ec2-stop-canary
  [✓] budgetDuration: PT2M (rationale: 2x the 60s stop action for rollback margin)
VERIFICATION_COMMANDS:
  aws fis get-experiment-template --id EXT-AAAA1111
  aws ec2 describe-instances --filters Name=tag:fis-target,Values=true --query 'Reservations[0].Instances[0].InstanceId'
  aws cloudwatch describe-alarms --alarm-names fis-stop-error-rate --query 'MetricAlarms[0].StateValue'
  aws iam get-role-policy --role-name fis-execution-role --policy-name fis-execution-policy
  aws logs describe-log-groups --log-group-name-prefix /aws/fis/ec2-stop-canary
```

### Perfect example output — PREREQUISITES_MISSING

```text
EXPERIMENT_TEMPLATE: ec2-stop-canary (action: aws:ec2:stop-instances, target: env=prod)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Intent + blast radius: Stop production instances for a drill, blast radius unknown
  [✗] Target scoped: resourceTags env=prod matches 247 instances — refusing to deploy with this filter. Switch to fis-target=true and tag only eligible resources.
  [✓] Action(s): aws:ec2:stop-instances (duration PT60S)
  [✗] Stop condition(s): no alarm name provided — without a stop condition, the experiment runs to budget with no auto-halt. Configure an error-rate or availability alarm.
  [—] IAM role: deferred until target scope is corrected
  [—] Logging: deferred
  [✗] budgetDuration: cannot set without target + stop-condition confirmation (PT2M recommended)
VERIFICATION_COMMANDS:
  aws ec2 describe-instances --filters Name=tag:env,Values=prod --query 'Reservations[*].Instances[0].InstanceId'
  aws cloudwatch describe-alarms --query 'MetricAlarms[?Namespace==`CWAgent`].AlarmName'
```

**Self-check before emit:**
- [ ] All 7 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] Target count is cited explicitly?
- [ ] Stop-condition alarm state + role permission both cited?
- [ ] IAM role cites tag conditions on action APIs?
- [ ] budgetDuration rationale ties to the action?
- [ ] Every `[✗]` cites the specific gap?
- [ ] terminate-instances (if present) carries a `[WARN]`?

## Recent AWS features

- **Aurora failover action (`aws:rds:failover-db-cluster`):** FIS can
  trigger an Aurora writer failover as a managed action. The failover
  takes 30-120 seconds; FIS does NOT roll it back. Use for RTO
  validation with explicit promotion acceptance.
- **EKS pod disruption via SSM:** FIS does not have a native
  `aws:eks:*` action in all regions; the canonical pattern is an
  `aws:ssm:start-automation-execution` or `aws:ssm:send-command` that
  runs `kubectl delete pod` on the EKS worker node via SSM. Verify
  the worker node has the SSM agent and kubeconfig.
- **Network actions (blackhole / latency / loss):** via SSM Run
  Command on EC2 or ECS ENIs, injecting iptables/tc rules. The
  network action's rollback depends on the SSM agent being reachable
  at action end — if offline, the rules persist. Always pair with a
  stop condition and a manual rollback runbook.
- **`aws:ec2:send-api-error`:** injects API errors for an IAM role
  (e.g., ThrottlingException on ssm:GetParameters). Useful for
  testing client retry logic without taking down the dependency.
  Scope the target by IAM role, not by resource.
- **Experiment logging to CloudWatch Logs and S3 (logSchemaVersion
  2):** emits structured JSON per experiment step. Configure both
  destinations; S3 for long-term retention, CloudWatch Logs for
  near-real-time anomaly detection on experiment outcomes.
- **Cross-account FIS via Organizations:** the FIS service-linked
  role can be shared across accounts in an Organization for
  centralized chaos engineering. Verify the trust policy includes
  the organization ID condition.

## AWS documentation

- **AWS Fault Injection Service User Guide** — https://docs.aws.amazon.com/fis/latest/userguide/
- **FIS Actions Reference** — https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html
- **FIS Target Types** — https://docs.aws.amazon.com/fis/latest/userguide/targets.html
- **FIS Stop Conditions** — https://docs.aws.amazon.com/fis/latest/userguide/stop-conditions.html
- **FIS IAM Roles** — https://docs.aws.amazon.com/fis/latest/userguide/iam-service-role.html
- **FIS Logging** — https://docs.aws.amazon.com/fis/latest/userguide/logging.html
- **FIS API Reference** — https://docs.aws.amazon.com/fis/latest/APIReference/
- **FIS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/fis/
- **Blog: AWS Resilience Hub + FIS** — https://aws.amazon.com/blogs/mt/test-application-resilience-using-aws-resilience-hub-and-aws-fault-injection-service/
- **Workshop: chaos engineering with FIS** — https://catalog.workshops.aws/chaosengineering
