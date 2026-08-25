---
name: dynamodb-autoscaling-deployer
description: 'Provisions DynamoDB auto-scaling with production defaults: target tracking for table (read/write capacity), target tracking for GSI (read/write capacity), auto-scaling role (application-autoscaling service-linked role), on-demand vs provisioned with auto-scaling decision, throttle metrics, scaling policy configuration (target utilization, scale-in cooldown, scale-out cooldown), CloudWatch alarms for throttling, latest DynamoDB on-demand vs provisioned capacity mode auto-switching. Emits a READY_TO_DEPLOY checklist with verification commands. Use when configuring DynamoDB auto- scaling for a table or GSI, setting up target tracking policies, choosing between on-demand and provisioned with auto-scaling, or monitoring throttle metrics. Triggers: dynamodb autoscaling, dynamodb target tracking, dynamodb capacity auto-scaling, gsi autoscaling, provisioned capacity autoscaling, dynamodb throttling, application autoscaling dynamodb, dynamodb on-demand vs provisioned.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with dynamodb, application-autoscaling, iam, and cloudwatch access. Works with Terraform aws_appautoscaling_policy / aws_appautoscaling_target resources and CloudFormation AWS::ApplicationAutoScaling::ScalingPolicy templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, dynamodb, autoscaling, cloudops, deploy, databases, provisioning, target-tracking, capacity, application-autoscaling
  dependencies: aws-orchestrator
  keywords: aws, dynamodb, autoscaling, auto-scaling, application autoscaling, cloudops, deploy, provisioning, target tracking, provisioned capacity, on-demand, gsi, global secondary index, throttle, capacity units, read capacity, write capacity, scaling policy, cloudwatch
  when_to_use: Invoke when the user wants to configure DynamoDB auto-scaling (target tracking scaling policies) for a table or GSI, set up the application-autoscaling service role, choose between on- demand and provisioned capacity mode, configure scaling policy parameters (target utilization, cooldowns), or monitor throttle metrics. Do NOT invoke for creating a DynamoDB table from scratch (use deploy-dynamodb-table), for auditing table configuration (use a DynamoDB auditor), or for DynamoDB Global Tables multi-region replication (separate feature).
---

# DynamoDB Auto-Scaling Deployer

An AWS CloudOps agent skill that provisions DynamoDB auto-scaling
with correct defaults. The skill walks the operator through capacity
mode selection (on-demand vs provisioned), target tracking policy
configuration for tables and GSIs, the application-autoscaling
service role, throttle monitoring, and scaling parameter tuning —
then emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

dynamodb autoscaling, dynamodb target tracking, dynamodb capacity
auto-scaling, GSI autoscaling, provisioned capacity autoscaling,
dynamodb throttling, application autoscaling dynamodb, dynamodb
on-demand vs provisioned, scaling policy cooldown, capacity mode
auto-switching.

## STRICT output contract

When this skill is invoked with a DynamoDB auto-scaling request
(table ARN, GSI name, capacity mode, target utilization, or a
partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `DYNAMODB_AUTOSCALING:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT
preface the checklist with prose, headings, or disclaimers — emit
the block as the first lines of the response. This contract is
what assertion-based evals and downstream provisioning pipelines
rely on; deviating from the literal labels breaks automation
silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — On-demand vs provisioned with auto-scaling | Capacity mode decision |
| Step 2 — Application auto-scaling role | IAM setup |
| Step 3 — Table target tracking (read/write) | Table scaling policy |
| Step 4 — GSI target tracking (read/write) | GSI scaling policy |
| Step 5 — Scaling policy parameters (utilization, cooldowns) | Tuning |
| Step 6 — Throttle metrics and monitoring | Observability |
| Step 7 — Recent features (capacity mode auto-switching) | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/target-tracking-and-cooldowns.md | Scaling policy deep dive |
| references/capacity-modes-and-throttling.md | On-demand vs provisioned + throttle metrics |

## Mindset

**One-line takeaway:** DynamoDB auto-scaling uses Application Auto
Scaling to adjust provisioned read/write capacity units based on
target utilization (typically 70%). It applies to PROVISIONED mode
tables and GSIs — NOT to on-demand tables. Target tracking is the
recommended scaling policy type; step scaling and simple scaling are
legacy.

Three misconceptions dominate DynamoDB auto-scaling misdesign:

- **"Auto-scaling works on on-demand tables."** It does not. Auto-
  scaling adjusts PROVISIONED capacity units (RCU/WCU). On-demand
  tables use `request_units` and scale automatically without
  policy configuration. You MUST set the table to PROVISIONED mode
  before attaching a scaling policy. Setting it back to on-demand
  detaches all scaling policies.

- **"Target utilization of 50% is the safe default."** 50% leaves
  half your provisioned capacity unused — you are paying for
  headroom you do not need. 70% is the AWS-recommended default
  for most workloads: it leaves enough buffer for burst absorption
  while minimizing over-provisioning. Use 50% only for spiky,
  unpredictable workloads where throttling is unacceptable.

- **"Table-level scaling covers GSIs."** It does not. Each GSI has
  its OWN independent RCU/WCU capacity. A table with auto-scaling
  on the table but NOT on its GSIs will throttle on the GSI even
  when the table is fine. You MUST configure separate scaling
  policies for EACH GSI.

## Configuration dependency graph (novel heuristic)
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic: target tracking lifecycle
Moved verbatim to [references/target-tracking-and-cooldowns.md](references/target-tracking-and-cooldowns.md) - load on demand (see References below).

## Expert heuristic: target utilization tuning
Moved verbatim to [references/target-tracking-and-cooldowns.md](references/target-tracking-and-cooldowns.md) - load on demand (see References below).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Table exists | Cannot attach scaling to a non-existent table | `aws dynamodb describe-table --table-name <name>` |
| Table ARN identified | Required for scalable target registration | `aws dynamodb describe-table --table-name <name> --query Table.TableArn` |
| Table in PROVISIONED mode | Auto-scaling does NOT work on on-demand tables | `aws dynamodb describe-table --table-name <name> --query Table.BillingModeSummary.BillingMode` |
| GSI names identified (if applicable) | Each GSI needs separate scaling policies | `aws dynamodb describe-table --table-name <name> --query Table.GlobalSecondaryIndexes[*].IndexName` |
| Current RCU/WCU known | Min/Max capacity envelope must bracket current values | `aws dynamodb describe-table --table-name <name> --query Table.[ProvisionedThroughput.ReadCapacityUnits,ProvisionedThroughput.WriteCapacityUnits]` |
| Application auto-scaling role | CloudFormation/CLI assumes this to adjust capacity | `aws iam get-role --role-name AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback` (auto-created SLR) |
| Target utilization decided | The key cost-vs-availability parameter | 70 (default), 50 (conservative), 90 (aggressive) |
| Min/Max capacity decided | Defines the scaling envelope | Min ≤ current ≤ Max |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — On-demand vs provisioned with auto-scaling

The first decision is whether to use on-demand or provisioned
capacity mode. Auto-scaling applies ONLY to provisioned mode.

**Decision tree:**

```text
Is the workload traffic predictable and steady?
├── YES → PROVISIONED with auto-scaling
│         Lower cost for steady workloads
│         Target tracking adjusts RCU/WCU automatically
│         Requires scaling policy configuration
└── NO  → Is the workload spiky and unpredictable?
    ├── YES → ON-DEMAND
    │         Scales instantly per-request (no policy needed)
    │         Higher cost per request but no idle capacity cost
    │         No auto-scaling configuration needed
    └── NO  → Start with ON-DEMAND, switch to PROVISIONED when
             traffic patterns stabilize
```

**Feature comparison:**

| Feature | On-demand | Provisioned with auto-scaling |
|---|---|---|
| Scaling | Instant (per request) | Target tracking (60s evaluation) |
| Cost model | Pay per request-unit | Pay per provisioned capacity-hour |
| Best for | Unpredictable, spiky, new workloads | Steady, predictable workloads |
| Throttle risk | Very low (scales instantly) | Low (with properly tuned policy) |
| Configuration | None (automatic) | Scaling policies per table + GSI |
| Cost optimization | Higher per-unit cost | Lower for steady workloads (can tune Min/Max) |

**Common mistake:** enabling auto-scaling on an on-demand table.
Auto-scaling policies only apply to PROVISIONED mode. If the table
is on-demand, switch to PROVISIONED first:
`aws dynamodb update-table --table-name <name> --billing-mode PROVISIONED`.

## Step 2 — Application auto-scaling role

Application Auto Scaling needs a service role to manage DynamoDB
capacity. For DynamoDB, this is a service-linked role that is auto-
created on first use.

**Verify the service-linked role exists:**

```bash
aws iam get-role \
  --role-name AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback
```

If it does not exist, registering the first scalable target will
auto-create it. You can also create it explicitly:

```bash
aws iam create-service-linked-role \
  --aws-service-name dynamodb.application-autoscaling.amazonaws.com
```
Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).


## Step 3 — Table target tracking (read/write)

Register scalable targets and create target tracking policies for
the table's read and write capacity.

**Register scalable targets:**

```bash
# Read capacity scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/my-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 40000

# Write capacity scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/my-table \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 \
  --max-capacity 40000
```

**Create target tracking policies:**

```bash
# Read capacity target tracking
aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/my-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name my-table-read-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "DynamoDBReadCapacityUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 60
  }'

# Write capacity target tracking
aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/my-table \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --policy-name my-table-write-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "DynamoDBWriteCapacityUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 60
  }'
```

**Key fields:**
- `--resource-id`: `table/<table-name>` for table-level scaling.
- `--scalable-dimension`: `dynamodb:table:ReadCapacityUnits` or
  `dynamodb:table:WriteCapacityUnits`.
- `--min-capacity` / `--max-capacity`: the scaling envelope. Min
  must be ≤ current provisioned; Max defines the ceiling.
- `TargetValue`: target utilization percentage (70 recommended).
- `PredefinedMetricType`: `DynamoDBReadCapacityUtilization` or
  `DynamoDBWriteCapacityUtilization` — these are managed metrics,
  NOT raw `ConsumedReadCapacityUnits`.
- `ScaleOutCooldown` / `ScaleInCooldown`: seconds between
  consecutive scaling actions.

## Step 4 — GSI target tracking (read/write)

Each GSI has its OWN independent capacity and needs separate
scaling policies. This is the most commonly missed configuration.

**Register GSI scalable targets:**

```bash
# GSI read capacity scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/my-table/index/my-gsi \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 10000

# GSI write capacity scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/my-table/index/my-gsi \
  --scalable-dimension dynamodb:index:WriteCapacityUnits \
  --min-capacity 5 \
  --max-capacity 10000
```

**Create GSI target tracking policies:**

```bash
aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/my-table/index/my-gsi \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --policy-name my-gsi-read-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "DynamoDBReadCapacityUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 60
  }'
```

**Key differences from table scaling:**
- `--resource-id`: `table/<table-name>/index/<gsi-name>` (includes
  the GSI name).
- `--scalable-dimension`: `dynamodb:index:ReadCapacityUnits` or
  `dynamodb:index:WriteCapacityUnits` (uses `index:` not `table:`).
- Each GSI needs its OWN pair of scalable targets and policies. A
  table with 3 GSIs needs 8 total scaling configurations (2 table +
  6 GSI).

**Common mistake:** configuring table auto-scaling but forgetting
GSI auto-scaling. The table scales fine but queries hitting the GSI
throttle because the GSI's capacity is static. ALWAYS configure
scaling for EVERY GSI.

## Step 5 — Scaling policy parameters (utilization, cooldowns)

Target tracking policies have three key tuning parameters.

| Parameter | Default | Range | Description |
|---|---|---|---|
| `TargetValue` | 70 | 10-90 | Target utilization percentage |
| `ScaleOutCooldown` | 60 | 0-3600 | Seconds between scale-OUT actions |
| `ScaleInCooldown` | 0 | 0-3600 | Seconds between scale-IN actions |

**TargetValue tuning:**
- **70** (recommended): balances cost and availability for most
  workloads. Leaves 30% headroom for bursts.
- **50** (conservative): for spiky workloads where throttling is
  unacceptable. Pays for 2x the steady-state capacity.
- **90** (aggressive): for cost-optimized workloads with
  predictable traffic. Minimal headroom; higher throttle risk.

**Cooldown tuning:**
- **ScaleOutCooldown=0**: scale out immediately when utilization
  exceeds target. Good for latency-sensitive workloads.
- **ScaleOutCooldown=60** (default): wait 60s between scale-out
  actions. Prevents over-scaling from metric noise.
- **ScaleInCooldown=0** (default for DynamoDB): reduce capacity
  immediately when utilization drops. Cost-optimal but may flap on
  oscillating workloads.
- **ScaleInCooldown=300**: wait 5 minutes between scale-in actions.
  Prevents flapping but delays cost reduction.

**Production recommendation:** TargetValue=70,
ScaleOutCooldown=60, ScaleInCooldown=60 for steady-state
workloads. This balances responsiveness with stability.

## Step 6 — Throttle metrics and monitoring

DynamoDB throttling occurs when consumed capacity exceeds
provisioned capacity. Monitor these metrics to detect under-
provisioning or auto-scaling gaps.

**Key CloudWatch metrics (AWS/DynamoDB namespace):**

| Metric | Description | When to alert |
|---|---|---|
| `ConsumedReadCapacityUnits` | Actual RCU consumed | Compare to ProvisionedReadCapacityUnits |
| `ConsumedWriteCapacityUnits` | Actual WCU consumed | Compare to ProvisionedWriteCapacityUnits |
| `ProvisionedReadCapacityUnits` | Provisioned RCU | Should track consumed closely |
| `ProvisionedWriteCapacityUnits` | Provisioned WCU | Should track consumed closely |
| `ThrottledRequests` | Count of throttled requests | Alert if > 0 |
| `ReturnedItemCount` | Items returned by queries/scans | Context for read consumption |
| `SystemErrors` | DynamoDB internal errors | Alert if > 0 |

**Throttle alarm:**
Moved verbatim to [references/capacity-modes-and-throttling.md](references/capacity-modes-and-throttling.md) - load on demand (see References below).

## Step 7 — Recent features
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## NEVER do these things

1. **NEVER enable auto-scaling on an on-demand table.** Auto-scaling
   policies apply ONLY to PROVISIONED mode tables. Switch to
   PROVISIONED first, then register scalable targets and create
   policies.

2. **NEVER forget GSI auto-scaling when configuring table auto-
   scaling.** Each GSI has independent RCU/WCU. A table with auto-
   scaling but GSI without it will throttle on GSI queries even
   when the table is fine. Configure scaling for EVERY GSI.

3. **NEVER set TargetValue below 50 for cost optimization.** A
   target below 50% means you provision 2x+ the consumed capacity,
   wasting cost. 70% is the recommended default; 50% is the
   conservative floor.

4. **NEVER set MaxCapacity above your account-level DynamoDB
   throughput limit.** `RegisterScalableTarget` will fail with
   `LimitExceededException`. Check the account limit before
   setting MaxCapacity.

5. **NEVER switch from PROVISIONED to on-demand without documenting
   scaling parameters.** The mode switch DETACHES all scaling
   policies. If you switch back to PROVISIONED, you must re-create
   all scalable targets and policies from scratch.

6. **NEVER use `ConsumedReadCapacityUnits` as the target tracking
   metric.** Target tracking for DynamoDB uses the pre-defined
   metrics `DynamoDBReadCapacityUtilization` and
   `DynamoDBWriteCapacityUtilization`. These are managed by
   Application Auto Scaling and account for the consumed-to-
   provisioned ratio.

7. **NEVER set ScaleInCooldown=0 for oscillating workloads.** A
   0-second scale-in cooldown means capacity drops immediately
   when utilization falls, which causes flapping on workloads
   with oscillating traffic. Use 60-300s for stability.

8. **NEVER assume MinCapacity is "free."** You pay for MinCapacity
   RCU/WCU continuously, even when the table is idle. Set
   MinCapacity to the minimum acceptable baseline, not to your
   peak capacity.

9. **NEVER use step scaling or simple scaling for DynamoDB.**
   Target tracking is the recommended and simplest policy type
   for DynamoDB. Step scaling and simple scaling are legacy,
   require manual CloudWatch alarm management, and are more error-
   prone.

10. **NEVER create a custom IAM role for DynamoDB auto-scaling
    unless required.** The service-linked role
    `AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback` is
    auto-created and has the correct permissions. Custom roles are
    error-prone and unnecessary for standard use cases.

## Output format

```text
DYNAMODB_AUTOSCALING: <table-name> (table-arn)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Table: <table-name> (arn:aws:dynamodb:<region>:<acct>:table/<name>)
  [✓|✗] Capacity mode: PROVISIONED (required for auto-scaling) | ON-DEMAND (auto-scaling not applicable)
  [✓|✗] Application auto-scaling role: AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback (SLR)
  [✓|✗] Table read scaling: scalable target (Min=<n>, Max=<n>) + policy (Target=<70%>, ScaleOut=<n>s, ScaleIn=<n>s)
  [✓|✗] Table write scaling: scalable target (Min=<n>, Max=<n>) + policy (Target=<70%>, ScaleOut=<n>s, ScaleIn=<n>s)
  [✓|✗] GSI <gsi-name> read scaling: scalable target (Min=<n>, Max=<n>) + policy (Target=<70%>)
  [✓|✗] GSI <gsi-name> write scaling: scalable target (Min=<n>, Max=<n>) + policy (Target=<70%>)
  [✓|✗] Throttle alarm: CloudWatch alarm on ThrottledRequests > 0 → <sns-arn>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws application-autoscaling describe-scalable-targets --service-namespace dynamodb --resource-ids table/<table-name>
  aws application-autoscaling describe-scaling-policies --service-namespace dynamodb --resource-id table/<table-name>
  aws dynamodb describe-table --table-name <table-name> --query Table.BillingModeSummary
  aws cloudwatch describe-alarms --namespace AWS/DynamoDB --dimensions Name=TableName,Value=<table-name>
```

### Worked example — table + GSI target tracking at 70%

```text
DYNAMODB_AUTOSCALING: orders-table (arn:aws:dynamodb:us-east-1:111111111111:table/orders-table)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Table: orders-table (arn:aws:dynamodb:us-east-1:111111111111:table/orders-table)
  [✓] Capacity mode: PROVISIONED (required for auto-scaling)
  [✓] Application auto-scaling role: AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback (SLR)
  [✓] Table read scaling: scalable target (Min=10, Max=40000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] Table write scaling: scalable target (Min=10, Max=40000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] GSI status-index read scaling: scalable target (Min=5, Max=20000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] GSI status-index write scaling: scalable target (Min=5, Max=20000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] Throttle alarm: CloudWatch alarm on ThrottledRequests > 0 → arn:aws:sns:us-east-1:111111111111:alerts
  [✓] Tags: Owner=platform, Service=orders
VERIFICATION_COMMANDS:
  aws application-autoscaling describe-scalable-targets --service-namespace dynamodb --resource-ids table/orders-table
  aws application-autoscaling describe-scaling-policies --service-namespace dynamodb --resource-id table/orders-table
  aws dynamodb describe-table --table-name orders-table --query Table.BillingModeSummary
  aws cloudwatch describe-alarms --namespace AWS/DynamoDB --dimensions Name=TableName,Value=orders-table
```

## Error handling
Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — configuration dependency graph + 2023-2026 features moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — API error remediation + role mistakes moved from SKILL.md
- [references/target-tracking-and-cooldowns.md](references/target-tracking-and-cooldowns.md) — lifecycle + utilization tuning heuristics moved from SKILL.md
- [references/capacity-modes-and-throttling.md](references/capacity-modes-and-throttling.md) — throttle alarm + consumed-vs-provisioned gap moved from SKILL.md

## Domain

AWS CloudOps / DynamoDB Capacity Auto-Scaling & Performance
Management.

## AWS documentation

- **DynamoDB auto-scaling** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html
- **Target tracking policies** — https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-target-tracking.html
- **Application Auto Scaling for DynamoDB** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.HowItWorks.html
- **On-demand vs provisioned** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html
- **DynamoDB metrics** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html
- **Capacity mode auto-switching** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html#AutoScaling.capacity-mode
