---
description: Operate AWS EC2 Spot Instance interruption handling — live interruption warning handling (2-minute notice), graceful-shutdown pipeline configuration (EventBridge + SQS + Lambda), capacity rebalance, allocation strategy tuning (capacity-optimized vs lowest-price), Spot Fleet auto-replacement, ASG capacity rebalance, stateful workload checkpointing (S3/DynamoDB), instance diversification across families and AZs, Spot placement score validation, and pipeline health auditing — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "Spot interruption warning"
  - "Spot Instance interrupted"
  - "2-minute warning Spot"
  - "graceful shutdown Spot"
  - "drain Spot from ELB"
  - "checkpoint Spot instance"
  - "capacity rebalance Spot"
  - "Spot Fleet replacement"
  - "ASG capacity rebalance"
  - "Spot placement score"
  - "instance diversification Spot"
  - "Spot Block deprecation"
  - "hibernate Spot instance"
  - "Spot graceful shutdown pipeline"
  - "Spot interruption queue"
routes_to: ec2-spot-interruption-operator
---

# /aws:operate-ec2-spot-interruption

Activate the `ec2-spot-interruption-operator` skill and plan/execute an
EC2 Spot Instance interruption handling operation with deterministic
pre-checks, CONFIRM gate, and post-verification.

## What it does

Reads a Spot Instance / Spot Fleet / ASG configuration plus the
intended operation and applies the priority-ordered pre-check sequence:

1. Pre-flight Spot/Fleet/ASG metadata gate — short-circuit cancelled
   requests, disabled EventBridge rules, and stale SQS queues.
2. Pre-check gate — REVIEW_REQUIRED if any check needs human attention
   (Lambda reserved concurrency = 0 stealth throttle, ELB deregistration
   delay too long for the 2-minute window, single-pool diversification,
   missing ASG lifecycle hook, allocation strategy change cost impact).
3. OPERATION_COMPLETED or REVIEW_REQUIRED — emit the exact CLI sequence
   with all flags populated, the expected side-effects (instance
   deregistered, checkpoint written, replacement launched), and the
   CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   monitor Lambda CloudWatch Logs and Spot Fleet status.
5. Post-verification — instance deregistered from ELB, checkpoint
   written to S3/DynamoDB, replacement launched and healthy, Spot Fleet
   capacity restored, application error rate within tolerance.
   OPERATION_COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

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
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <monitoring, diversification recommendation, caveats>
```

## When to invoke

Paste a Spot/Fleet/ASG configuration plus the intended operation, or
just describe the scenario and ask any of:

- "handle the Spot interruption warning for i-0abc123"
- "configure a graceful-shutdown pipeline for our Spot ASG"
- "switch from lowest-price to capacity-optimized"
- "audit our Spot Fleet diversification"
- "validate the Spot placement score before launching"
- "enable capacity rebalance on our ASG"
- "check if the interruption pipeline is healthy"

A bare instance ID + any Spot interruption verb ("Spot interrupted",
"graceful shutdown") also routes here via the orchestrator.

## Inputs

- Spot Instance Request (`describe-spot-instance-requests` JSON):
  `State`, `InstanceId`, `InstanceInterruptionBehavior`,
  `LaunchSpecification`.
- Spot Fleet config (`describe-spot-fleet-requests` JSON):
  `AllocationStrategy`, `TargetCapacity`, `FulfilledCapacity`,
  `LaunchTemplateConfigs`.
- ASG config (`describe-auto-scaling-groups` JSON):
  `CapacityRebalance`, `MixedInstancesPolicy`, lifecycle hooks.
- EventBridge rule (`describe-rule`): `State`, `EventPattern`.
- SQS queue (`get-queue-attributes`): queue depth, oldest message age,
  DLQ.
- Lambda (`get-function-configuration`): `State`, `Timeout`,
  `ReservedConcurrentExecutions`.
- ELB target group (`describe-target-group-attributes`):
  `deregistration_delay.timeout_seconds`.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[REVIEW]` per check and the specific
  item to review.
- For OPERATION_COMPLETED: POST_VERIFY list with `[PASS]` per check,
  the replacement instance ID, checkpoint verification, Spot Fleet
  capacity status, application error rate, monitoring recommendations.
- For REVIEW_REQUIRED: the specific items requiring human review
  (allocation strategy cost impact, arm64 support, ELB delay change,
  lifecycle hook addition, capacity rebalance enablement) and the
  remediation steps.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for EC2 Spot interruption handling).
- `/aws:deploy-ec2-spot-fleet` for the deploy-side counterpart —
  provisioning new Spot Fleets with diversification pre-configured.
- `/aws:optimize-ec2-rightsizing` for the optimize-side counterpart —
  right-sizing instances for cost and availability.
