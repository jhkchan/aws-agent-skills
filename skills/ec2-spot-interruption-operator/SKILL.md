---
name: ec2-spot-interruption-operator
description: Operates Amazon EC2 Spot Instance interruption handling workflows end-to-end — EventBridge Instance Interruption Warning (2-minute notice), Spot Instance Interruption Queue (SQS), Lambda functions for graceful shutdown (drain from ELB, checkpoint state to S3 or DynamoDB), capacity rebalance notifications, replacement strategy selection (capacity-optimized vs diversified vs lowest-price), Spot Fleet auto-replacement, Auto Scaling Group capacity rebalance, stateful workload checkpointing patterns (S3 multipart, DynamoDB point-in-time), Spot Block deprecation awareness, Spot placement score for capacity assessment, instance diversification across families and AZs (minimum 3 families for 99.9% availability), hibernate vs stop vs terminate on interruption behavior, and integration with Application Load Balancer / Network Load Balancer connection draining. Runs deterministic pre-checks (EventBridge rule health, SQS queue depth, Lambda concurrency, deregister delay, lifecycle hook timeout) behind a CONFIRM gate...
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws ec2 describe-spot-instance-requests, describe-spot-fleet- requests, describe-instances, modify-spot-fleet-request, aws events put-rule, put-targets, aws sqs receive-message, delete-message, get-queue-attributes, aws lambda get-function-configuration, invoke, aws autoscaling describe-auto-scaling-groups, put-lifecycle-hook, aws...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPERATION_COMPLETED | REVIEW_REQUIRED
  when_to_use: 'Handling a live Spot Instance Interruption Warning (the 2-minute notice), configuring an EventBridge rule plus SQS queue plus Lambda pipeline for graceful shutdown, tuning a Spot Fleet or ASG for capacity rebalance and auto-replacement, selecting a replacement strategy (capacity-optimized, diversified, lowest-price), validating Spot placement score before a launch, auditing instance diversification across families and AZs (target: minimum 3 instance families for 99.9% availability), configuring stateful workload checkpointing to S3 or DynamoDB, or auditing the interruption-handling pipeline health.'
  activation_triggers: Spot interruption warning, Spot Instance interrupted, 2-minute warning Spot, graceful shutdown Spot, drain Spot from ELB, checkpoint Spot instance, capacity rebalance Spot, Spot Fleet replacement, ASG capacity rebalance, Spot placement score, instance diversification Spot, Spot Block deprecation, hibernate Spot instance, Spot graceful shutdown pipeline, Spot interruption queue
  invocation_schema: 'Input: either (a) a Spot Instance or Spot Fleet configuration (describe-spot-instance-requests, describe-spot-fleet-requests, or describe-auto-scaling-groups output) plus the intended operation (handle-interruption, configure-pipeline, tune-replacement-strategy, audit-diversification, validate-placement-score, configure-checkpointing, audit-pipeline-health), OR (b) an EventBridge Instance Interruption Warning event for live handling. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per operation, where VERDICT is OPERATION_COMPLETED or REVIEW_REQUIRED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Spot Instance, Spot interruption, 2-minute warning, Instance Interruption Warning, EventBridge Spot, SQS interruption queue, graceful shutdown, drain from ELB, checkpoint state, capacity rebalance, capacity-optimized, diversified allocation, Spot Fleet, ASG capacity rebalance, stateful checkpointing, Spot placement score, instance diversification, hibernate on interruption, Spot Block deprecation, Spot two-minute warning
  tags: aws, ec2, spot, compute, interruption, autoscaling, eventbridge, operate
---

# EC2 Spot Instance Interruption Operator

## What this skill does

Executes EC2 Spot Instance interruption-handling operations correctly and
safely. Runs deterministic pre-checks before any state-changing CLI
(EventBridge rule is ENABLED, SQS queue is healthy with acceptable depth,
Lambda graceful-shutdown function is Active with sufficient concurrency,
ALB/NLB target group deregistration delay is configured, ASG lifecycle
hook timeout accommodates the 2-minute window, Spot Fleet or ASG has a
valid replacement strategy with sufficient diversification), executes
the graceful-shutdown pipeline behind a CONFIRM gate, and verifies the
result by confirming the interrupted instance was drained from the load
balancer, state was checkpointed, replacement launched, and the
application's error rate stayed within the tolerance band. Every
interruption-warning handler produces the drain-and-checkpoint sequence;
every fleet tuning surfaces the capacity-optimized recommendation and
the 3-family diversification minimum.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (REVIEW_REQUIRED/OPERATION_COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why the 2-minute warning is the safety window, capacity-optimized as the default, diversification math | Understanding the safety model |
| **§ Pre-flight** | Spot/Fleet/ASG metadata gate — state, capacity, allocation strategy, diversification | Before executing any CLI |
| **§ Process** | Per-operation planning: handle-interruption, configure-pipeline, tune-replacement, audit-diversification, validate-placement, configure-checkpointing, audit-health | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that lose in-flight work or strand the fleet below capacity | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, verify pipeline health, validate checkpoint target | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `REVIEW_REQUIRED` | Operation plan is ready but requires human review before execution (replacing lowest-price with capacity-optimized changes billing behavior, reducing a Spot Fleet's target capacity below current running count, changing the interruption behavior from terminate to hibernate or stop, modifying an ASG lifecycle hook that affects in-flight deployments, enabling capacity rebalance on a production ASG) | Emit plan with the specific items to review, wait for operator approval |
| `OPERATION_COMPLETED` | Interruption handling finished and post-verification passed (instance drained from ELB, state checkpointed to S3 or DynamoDB, replacement launched, ASG/Fleet capacity restored, application error rate within tolerance) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, any failure routes
to REVIEW_REQUIRED with the failure surfaced):**

1. **Spot request reachability** — the Spot Instance Request exists and
   `State: active` (not `cancelled`, `closed`, `failed`). The instance
   itself is `running`.
2. **EventBridge rule health** — the
   `EC2 Spot Instance Interruption Warning` rule is `ENABLED`, targets
   the SQS queue or Lambda function, and the rule's event pattern
   matches `"detail-type": ["EC2 Spot Instance Interruption Warning"]`.
3. **SQS queue health** — the interruption queue is healthy:
   `ApproximateNumberOfMessagesVisible` is not climbing (no consumer
   lag), `ApproximateAgeOfOldestMessage` is under the 2-minute window
   threshold, the dead-letter queue is empty.
4. **Lambda graceful-shutdown function** — `State: Active`,
   `ReservedConcurrentExecutions >= 1` (not the stealth-throttle
   condition), timeout >= 60 seconds (enough for drain + checkpoint
   within the 2-minute window), runtime is a supported version.
5. **ALB/NLB target group** — the instance is a registered target,
   `deregistration_delay.timeout_seconds` is set to a value that allows
   in-flight requests to complete (typically 30-60 seconds).
6. **ASG lifecycle hook** — if the instance is in an ASG, the
   `InstanceLaunching` and `InstanceTerminating` lifecycle hooks have
   timeouts that accommodate the 2-minute window (default 60 minutes
   for launching, but the termination hook should be at least 120
   seconds to give the graceful-shutdown pipeline room).
7. **Replacement strategy** — the Spot Fleet or ASG has a valid
   allocation strategy (`capacity-optimized` recommended,
   `capacity-optimized-prioritized`, `diversified`,
   `lowest-price` with multiple pools).
8. **Diversification** — the Spot Fleet or ASG specifies at least 3
   instance families across at least 3 AZs (the minimum for 99.9%
   availability per the AWS Spot best-practices guidance).
9. **Capacity rebalance** — `AllocationStrategy` on the ASG or Spot
   Fleet supports capacity rebalance (or is explicitly enabled via
   `CapacityRebalance` on the ASG).

**Cost/time baselines (2026):**

- EventBridge Instance Interruption Warning: delivered 2 minutes (120
  seconds) before the actual interruption. This is the maximum
  graceful-shutdown window. Some interruption types (capacity-reclaim)
  may provide less notice in practice — design for 90 seconds to be
  safe.
- ELB target deregistration: enters `draining` state, waits
  `deregistration_delay.timeout_seconds` (default 300 seconds for ALB,
  configurable 0-3600). Within the 2-minute window, set this to 30-60
  seconds to leave room for checkpointing.
- Lambda graceful-shutdown execution: typically 10-45 seconds (drain
  from ELB, write checkpoint to S3, signal the application to flush).
- Spot Fleet auto-replacement: the Fleet launches a replacement within
  seconds of the interruption. Provisioning time depends on the AMI
  and instance type (30 seconds to 3 minutes).
- Spot placement score: a single API call
  (`get-spot-placement-scores`) returns in under 5 seconds for up to
  50,000 capacity combinations.

## Mindset

**One-line takeaway:** the 2-minute Instance Interruption Warning is
the safety window — it is enough time to drain from the load balancer
and checkpoint state, but only if the pipeline is pre-wired and tested.
Spot is NOT unreliable; it is a different reliability model that
rewards diversification and graceful shutdown. Driven by three EC2
Spot realities:

- **The 2-minute warning allows graceful shutdown (drain + checkpoint).**
  When EC2 reclaims a Spot Instance, EventBridge emits an
  `EC2 Spot Instance Interruption Warning` event 2 minutes before the
  actual interruption. A Lambda function (or any event consumer) can
  use this window to deregister the instance from the load balancer,
  flush in-flight transactions, write a checkpoint to S3 or DynamoDB,
  and signal the application to shut down cleanly. Without this
  pipeline, the instance is terminated with no warning and all in-
  flight work is lost.

- **Capacity-optimized allocation strategy minimizes interruptions.**
  The `capacity-optimized` strategy (and its
  `capacity-optimized-prioritized` variant) launches Spot Instances
  from the pools with the lowest interruption rates, rather than the
  lowest price. This reduces the frequency of interruptions at a
  marginally higher cost. For production workloads, capacity-optimized
  is the default recommendation — the cost saving from `lowest-price`
  is eaten by the disruption of frequent interruptions.

- **Diversify across at least 3 instance families for 99.9%
  availability.** Spot interruption rates vary by instance family, AZ,
  and time of day. A fleet that runs on a single instance type in a
  single AZ is at high risk of a simultaneous reclaim. Diversifying
  across at least 3 instance families (e.g., `m5`, `m6a`, `c6g`) and
  at least 3 AZs gives a 99.9% availability profile for Spot — the
  mathematical basis is that the probability of all pools being
  interrupted simultaneously drops exponentially with the number of
  independent pools.

## Pre-flight: Spot/Fleet/ASG metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-spot-instance-requests` paginates at 1,000/page
— drain `--next-token` to completion. Filter by `--state active`.

**Live-account pre-flight (skip if offline plan audit):** the 7 read-only commands
(describe-spot-instance-requests ... autoscaling describe-auto-scaling-groups) are listed in [Diagnostic commands](references/diagnostic-commands.md).

Malformed-input protocol (VERDICT: ERROR + REMEDIATION): see [Error handling](references/error-handling.md).

| Spot/Fleet/ASG attribute | Effect on operation |
|---|---|
| `State: cancelled` or `closed` | Spot request no longer active. Instance may still be running but is not managed by the Spot service. |
| `InstanceInterruptionBehavior: terminate` | Default. Instance is terminated on interruption. No state preserved. |
| `InstanceInterruptionBehavior: stop` | Instance is stopped (EBS-backed only). Can be restarted when capacity returns. |
| `InstanceInterruptionBehavior: hibernate` | Instance hibernates (memory state saved to EBS). Requires the instance to be hibernation-enabled at launch. |
| EventBridge rule `State: DISABLED` | Interruption warnings are NOT delivered. The graceful-shutdown pipeline is dark. |
| SQS `ApproximateAgeOfOldestMessage > 120` | Messages are older than the 2-minute window — the consumer (Lambda) is lagging. Interruption warnings in the queue are already stale. |
| Lambda `ReservedConcurrentExecutions: 0` | Stealth throttle. The graceful-shutdown Lambda will never execute. Every interruption is a hard termination. |
| Lambda `Timeout < 60` | May not complete drain + checkpoint within the 2-minute window. |
| Spot Fleet `AllocationStrategy: lowestPrice` with 1 pool | High interruption risk. Recommend switching to capacity-optimized with >= 3 pools. |
| Spot Fleet `FulfilledCapacity < TargetCapacity` | Fleet is below target — instances are being interrupted faster than replacements launch. |
| ASG `CapacityRebalance: false` | Capacity rebalance is off. The ASG does not proactively replace at-risk instances. |
| ASG `MixedInstancesPolicy` with 1 instance type | No diversification. High risk of simultaneous reclaim. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge - non-obvious EC2 Spot interruption behaviors (condensed)

- The 2-minute warning is a maximum, not a guarantee - design the pipeline to finish within 90 seconds. EventBridge is the ONLY notification channel.
- `InstanceInterruptionBehavior` is set at launch and immutable (terminate / stop / hibernate).
- Capacity rebalance is proactive (launches replacements BEFORE the warning). Prefer `capacity-optimized` over `lowest-price` for production.
- Diversification math: 3 families x 3 AZs = 9 pools for 99.9% availability. Spot placement score is a forecast, not a guarantee.
- Spot Block is deprecated (2024+). ELB deregistration delay must fit within 2 minutes; lifecycle hooks fire on termination, not the warning.
- Full deep dives (Graviton rates, StatusCode early warning, Fleet auto-replacement): [Advanced patterns](references/advanced-patterns.md).

### Step 1: Pre-check gate — REVIEW_REQUIRED if any check needs human attention

Run ALL pre-checks for the chosen operation. If any check fails or
requires human review, the verdict is REVIEW_REQUIRED with the specific
items listed. Do NOT execute until the operator reviews.

**For ALL operations:**
1. Spot Instance Request exists and `State: active`.
2. Instance is `running`.
3. EventBridge interruption-warning rule is `ENABLED`.
4. SQS queue (or Lambda target) is healthy — no consumer lag.

**For handle-interruption (live EventBridge warning event):**
5. Event `detail.instance-action` determines shutdown sequence
   (`terminate`, `stop`, or `hibernate`).
6. Instance registered to a target group. Lambda `Active` with
   reserved concurrency >= 1, timeout >= 60. Checkpoint target exists.
7. The 2-minute window has not already elapsed.

**For configure-pipeline (set up EventBridge + SQS + Lambda):**
5. EventBridge pattern matches `"EC2 Spot Instance Interruption
   Warning"`. SQS queue has DLQ configured.
6. Lambda timeout >= 60. Lambda role has `ec2:DescribeInstances`,
   `elasticloadbalancing:DeregisterTargets`, `s3:PutObject`.
7. Target group `deregistration_delay.timeout_seconds` is 30-60s.

**For tune-replacement-strategy (modify Fleet or ASG):**
5. Current `AllocationStrategy` identified. Proposed strategy is
   `capacity-optimized` (recommended) or `diversified` with >= 3 pools.
6. For ASGs: `CapacityRebalance` enabled. `ExcessCapacityTerminationPolicy`
   reviewed (default `true`).

**For audit-diversification (read-only):**
5. Fleet/ASG `Overrides` lists all instance types and AZs.
6. Count of unique instance families >= 3, unique AZs >= 3.
   Graviton included (recommended).

**For validate-placement-score (read-only):**
5. `get-spot-placement-scores` called. Score >= 7 good, 4-6 marginal,
   <= 3 avoid.

**For configure-checkpointing (stateful workload):**
5. Checkpoint target exists. Application supports checkpoint signals
   (SIGTERM handler). Checkpoint frequency configured. Restore path
   tested.

**For audit-pipeline-health (read-only):**
5. EventBridge `ENABLED`. SQS `ApproximateAgeOfOldestMessage` < 120s.
   DLQ empty. Lambda `Active`, reserved concurrency >= 1. ELB delay
   30-60s.

Interruption-handling failure-mode table (Lambda never invoked, ELB still sending traffic, Fleet did not auto-replace, etc.): see [Error handling](references/error-handling.md).

### Step 2: OPERATION_COMPLETED or REVIEW_REQUIRED — emit operation plan

If all pre-checks pass AND the operation is read-only or low-risk
(audit-diversification, validate-placement-score, audit-pipeline-health,
handle-interruption where the pipeline executes successfully), emit
`VERDICT: OPERATION_COMPLETED` (for already-finished operations) or
the executable plan with the CONFIRM gate.

For operations requiring human review (tune-replacement-strategy changes
the allocation strategy, configure-pipeline on a production ASG, enabling
capacity rebalance, changing `InstanceInterruptionBehavior`), emit
`VERDICT: REVIEW_REQUIRED` with the specific items to review. The plan
includes:

- The exact AWS CLI command with all flags populated from the Spot/Fleet/
  ASG configuration.
- The expected duration (Lambda execution 10-45 seconds; Spot Fleet
  replacement launch 30 seconds to 3 minutes; ASG capacity rebalance
  proactive replacement within minutes).
- The expected side-effects (instance deregistered, replacement launched,
  capacity restored, checkpoint written).
- The CONFIRM gate prompt.
- The monitoring step (CloudWatch metrics for `SpotInstanceInterruptionCount`,
  ELB `HealthyHostCount`, Lambda errors).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`modify-spot-fleet-request`, `deregister-targets`,
  `update-function-configuration`, `put-rule`, `put-targets`,
  `update-auto-scaling-group`, `put-lifecycle-hook`,
  `terminate-instances`), emit: `CONFIRM: About to <operation> on
  <target> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.
- Capture pre-state for audit: `aws ec2 describe-spot-instance-requests
  --spot-instance-request-id <id> --output json > /tmp/<id>-pre-$(date
  +%s).json`.
- For handle-interruption: the Lambda function is invoked by
  EventBridge (or manually for testing). The Lambda deregisters the
  instance from the ELB, writes a checkpoint, and signals the
  application to shut down. Monitor via:
  `aws logs tail /aws/lambda/<fn> --follow --since 2m`.
- For tune-replacement-strategy: execute the
  `modify-spot-fleet-request` or `update-auto-scaling-group`. The
  change is immediate — new launches use the new strategy. Existing
  instances are not restarted.

### Step 4: Post-verification — OPERATION_COMPLETED

After the operation finishes, run post-verification. ALL checks must
pass for `OPERATION_COMPLETED`.

1. For handle-interruption: confirm the instance was deregistered from
   the ELB (`describe-target-health` shows `TargetHealth.State: unused`
   or the target is gone), the checkpoint was written to S3 or
   DynamoDB (verify the object or item exists with a recent
   timestamp), and the replacement launched (Spot Fleet
   `FulfilledCapacity` is back to `TargetCapacity`, or ASG
   `DesiredCapacity` is met).
2. For configure-pipeline: test the pipeline by emitting a synthetic
   interruption event (`aws events put-events` with a test payload) and
   confirm the Lambda executes successfully.
3. For tune-replacement-strategy: confirm the
   `AllocationStrategy` changed via `describe-spot-fleet-requests` or
   `describe-auto-scaling-groups`. Monitor for the next 24 hours —
   the interruption rate should decrease with `capacity-optimized`.
4. For audit-diversification: report the count of unique instance
   families and AZs. Flag if below the 3 x 3 minimum.
5. For audit-pipeline-health: report the health of each component
   (EventBridge, SQS, Lambda, ELB target group, ASG lifecycle hook).
6. Application error rate: confirm the ELB `HTTPCode_ELB_5XX_Count`
   and `TargetConnectionErrorCount` metrics did not spike during the
   interruption handling window.
7. Checkpoint integrity: for stateful workloads, verify the
   replacement loaded the checkpoint and resumed from the correct
   state.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim OPERATION_COMPLETED. A failed verification
typically means the pipeline is misconfigured (Lambda timeout, missing
permissions, ELB delay too long) or the diversification is insufficient.

## Output format (per operation)

```text
OPERATION: <handle-interruption | configure-pipeline | tune-replacement-strategy | audit-diversification | validate-placement-score | configure-checkpointing | audit-pipeline-health>
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
TARGET: <spot-instance-id-or-fleet-id-or-asg-name> (strategy: <current>, target: <target-config>)
PRE_CHECKS:
  - [PASS] <check description>
  - [REVIEW] <check description> — <item to review>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <monitoring, caveats, diversification recommendation>
```

### Worked example — handle-interruption (OPERATION_COMPLETED)

```text
OPERATION: handle-interruption
VERDICT: OPERATION_COMPLETED
TARGET: i-0abc123def456 (Spot Fleet: sfr-abc123, ASG: prod-web-asg)
PRE_CHECKS:
  - [PASS] EventBridge warning received: instance-action=terminate,
    event time 2026-08-11T14:23:00Z (105 seconds remaining in window)
  - [PASS] Instance i-0abc123def456 registered to target group
    arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/prod-web-tg/...
  - [PASS] Graceful-shutdown Lambda prod-spot-shutdown State: Active,
    Timeout: 90, ReservedConcurrentExecutions: 10
  - [PASS] Lambda execution role has elasticloadbalancing:DeregisterTargets,
    s3:PutObject on arn:aws:s3:::prod-checkpoints/*
  - [PASS] ELB deregistration_delay.timeout_seconds: 45 (fits within
    the 2-minute window)
  - [PASS] ASG InstanceTerminating lifecycle hook HeartbeatTimeout: 120
STEPS:
  1. Lambda prod-spot-shutdown invoked by EventBridge at 14:23:01Z.
  2. Lambda deregistered i-0abc123def456 from target group
     (deregistration draining started at 14:23:03Z).
  3. Lambda sent SIGTERM to the application process (via SSM
     SendCommand) — application flushed in-flight requests and wrote
     checkpoint to s3://prod-checkpoints/i-0abc123def456/state.json
     (completed 14:23:38Z).
  4. ELB target entered "unused" state at 14:23:48Z (45s drain).
  5. Instance terminated by Spot service at 14:25:00Z.
  6. ASG launched replacement i-0new456 (capacity-optimized, m6a.large
     in us-east-1b) at 14:25:15Z. Replacement "running" at 14:27:45Z.
  7. Replacement registered to target group, health checks passing at
     14:28:30Z.
POST_VERIFY:
  - [PASS] i-0abc123def456 deregistered from target group
  - [PASS] Checkpoint written: s3://prod-checkpoints/i-0abc123def456/state.json
    (timestamp 2026-08-11T14:23:38Z)
  - [PASS] Spot Fleet FulfilledCapacity: 10 (matches TargetCapacity)
  - [PASS] Replacement i-0new456 TargetHealth.State: healthy
  - [PASS] ELB HTTPCode_ELB_5XX_Count: no spike during the window
  - [PASS] Application resumed from checkpoint on replacement
NOTES:
  - Total handling time: 35 seconds (deregister + checkpoint + flush).
    Well within the 2-minute window.
  - Spot Fleet auto-replaced the interrupted instance via the
    capacity-optimized allocation strategy. Replacement launched in
    us-east-1b (different AZ from the interrupted instance, which was
    in us-east-1a).
  - The ASG CapacityRebalance was enabled — a proactive replacement
    was already in progress when the interruption warning fired,
    reducing the effective gap to zero.
```

## Anti-Patterns — NEVER

- NEVER rely on Spot without a graceful-shutdown pipeline. Without
  EventBridge + a consumer, the instance is terminated with no warning.
  The 2-minute warning is the ONLY notification channel.

- NEVER set the ELB deregistration delay longer than the 2-minute
  window. The default ALB delay of 300 seconds means the instance is
  terminated before draining finishes. Set to 30-60 seconds for Spot.

- NEVER use `lowest-price` with a single pool for production. Use
  `capacity-optimized` with 3+ families across 3+ AZs. The 5-8% cost
  premium is offset by the 5-10x reduction in interruptions.

- NEVER assume the 2-minute warning is always exactly 120 seconds.
  Design the pipeline to complete within 90 seconds.

- NEVER change `InstanceInterruptionBehavior` on a running instance —
  it is set at launch and immutable.

- NEVER forget the Lambda resource-based policy for EventBridge
  (`events.amazonaws.com`). Without it, direct Lambda invocation fails
  silently.

- NEVER use Spot Block for new capacity — it is deprecated (2024+).
  Use On-Demand Capacity Reservations for predictable capacity.

- NEVER rely on hibernate as the only state-preservation. Hibernate
  saves memory to EBS but EC2 may terminate the instance afterward.
  Use application-level checkpointing to S3 or DynamoDB.

- NEVER ignore SQS queue depth. Messages older than 120 seconds are
  stale — the instance is already terminated. Set a CloudWatch alarm.

- NEVER diversify across instance types within a single family only.
  `c5.large`, `c5.xlarge`, `c5.2xlarge` share the same pools. Mix
  families (`c5`, `m5`, `c6g`) for true independence.

- NEVER assume Spot Fleet auto-replacement restores state. Replacements
  start from scratch — stateful workloads must checkpoint independently.

- NEVER auto-execute a state-changing Spot CLI without the CONFIRM gate.
  Allocation strategy, target capacity, and interruption behavior
  changes affect billing and availability.

- NEVER assume capacity rebalance eliminates all interruptions. It is
  proactive but cannot prevent every reclaim. The graceful-shutdown
  pipeline is still required.

- NEVER forget to test the pipeline with a synthetic event. The first
  real interruption is NOT the time to discover the pipeline is broken.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-spot-fleet-request`, `update-auto-scaling-group`,
  `put-lifecycle-hook`, `modify-target-group-attributes`,
  `terminate-instances`, `deregister-targets`,
  `update-function-configuration`, `put-rule`, `put-targets`),
  emit: `CONFIRM: About to <operation> on <target> in account
  <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`.

- **Capture pre-state for audit.** `describe-spot-fleet-requests` or
  `describe-auto-scaling-groups` JSON saved to `/tmp/<id>-pre-$(date
  +%s).json`.

- **Verify pipeline health.** EventBridge rule `ENABLED`. SQS queue
  depth stable, oldest message under 120s, DLQ configured. Lambda
  `State: Active`, `Timeout >= 60`, reserved concurrency not 0. ELB
  `deregistration_delay.timeout_seconds` 30-60s for Spot targets. ASG
  lifecycle hook `HeartbeatTimeout >= 120`.

- **Verify diversification.** At least 3 instance families across 3
  AZs. Use `capacity-optimized` allocation strategy. Enable
  `CapacityRebalance` on ASGs for proactive replacement.

## References (load on demand)

- [Worked examples](references/worked-examples.md) - tune-replacement-strategy (REVIEW_REQUIRED) and configure-pipeline walkthroughs
- [Error handling](references/error-handling.md) - failure-mode table and malformed-input VERDICT: ERROR protocol
- [Diagnostic commands](references/diagnostic-commands.md) - live-account pre-flight command listing
- [Advanced patterns](references/advanced-patterns.md) - expert behaviors and 2024-2026 feature notes
- [Diversification and strategy](references/diversification-and-strategy.md) - allocation strategies, diversification math, placement score
- [Graceful shutdown pipeline](references/graceful-shutdown-pipeline.md) - EventBridge + SQS + Lambda architecture and checkpointing

## Domain

AWS CloudOps / EC2 Spot Instance Interruption Handling, Graceful
Shutdown & Capacity Resilience.

## AWS documentation

- **Amazon EC2 Spot Instances** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html
- **Spot Instance interruption notices** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-interruptions.html
- **Best practices for Spot Instances** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html
- **Spot Fleet** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-fleet.html
- **Capacity Rebalance** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/capacity-rebalance.html
- **Spot Instance interruption handling** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/handling-spot-interruptions.html
- **Spot Placement Score** — https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_GetSpotPlacementScores.html
- **EventBridge EC2 Spot Instance Interruption Warning** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event.html#eb-spot-instance
- **Auto Scaling lifecycle hooks** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html
- **ELB target group deregistration delay** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#deregistration-delay
