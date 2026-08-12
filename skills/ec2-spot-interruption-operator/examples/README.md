# End-to-end usage scenario: ec2-spot-interruption-operator

A walkthrough showing the skill handling a live Spot Instance
Interruption Warning with a fully-wired graceful-shutdown pipeline, and
the contrast case where Lambda reserved concurrency = 0 silently
disables the pipeline.

## Input (user prompt)

> We just got a Spot interruption warning for `i-0abc123def456` in our
> `prod-web-asg`. The graceful-shutdown Lambda should be handling it.
> Can you verify the pipeline is working and the replacement is
> launching?

```json
{
  "Operation": "handle-interruption",
  "Event": {
    "detail-type": "EC2 Spot Instance Interruption Warning",
    "source": "aws.ec2",
    "time": "2026-08-11T14:23:00Z",
    "detail": {
      "instance-id": "i-0abc123def456",
      "instance-action": "terminate"
    }
  },
  "InstanceMetadata": {
    "InstanceType": "m6a.large",
    "AvailabilityZone": "us-east-1a",
    "SpotFleet": "sfr-prod-web",
    "ASG": "prod-web-asg"
  },
  "PipelineHealth": {
    "EventBridgeRule": "spot-interruption-warning (ENABLED)",
    "Lambda": "prod-spot-shutdown (Active, Timeout: 90, ReservedConcurrency: 10)",
    "ELBDeregistrationDelay": 45,
    "ASGLifecycleHook": "spot-termination-hook (HeartbeatTimeout: 120)",
    "CapacityRebalance": true
  }
}
```

## Skill output

```text
OPERATION: handle-interruption
VERDICT: OPERATION_COMPLETED
TARGET: i-0abc123def456 (Spot Fleet: sfr-prod-web, ASG: prod-web-asg)
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
  3. Lambda sent SIGTERM to the application via SSM SendCommand —
     application flushed in-flight requests and wrote checkpoint to
     s3://prod-checkpoints/i-0abc123def456/state.json (14:23:38Z).
  4. ELB target entered "unused" state at 14:23:48Z (45s drain).
  5. Instance terminated by Spot service at 14:25:00Z.
  6. ASG launched replacement i-0new456 (capacity-optimized, m6a.large
     in us-east-1b) at 14:25:15Z. "running" at 14:27:45Z.
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
    Well within the 90-second safety margin.
  - CapacityRebalance was enabled — a proactive replacement was
    already in progress when the warning fired, reducing the gap to
    near-zero.
  - The replacement launched in us-east-1b (different AZ from the
    interrupted instance in us-east-1a), demonstrating the
    diversification working as designed.
```

## Contrast — REVIEW_REQUIRED case (reserved concurrency = 0)

If the Lambda had `ReservedConcurrentExecutions: 0`, the pre-check
gate would surface the stealth throttle:

```text
OPERATION: audit-pipeline-health
VERDICT: REVIEW_REQUIRED
TARGET: prod-api-asg
PRE_CHECKS:
  - [PASS] EventBridge rule spot-interruption-warning: ENABLED
  - [PASS] SQS queue spot-interruption-queue: exists
  - [FAIL] SQS ApproximateAgeOfOldestMessage: 340 seconds (stale —
    past the 2-minute window). Messages in the queue are from
    interruptions that already terminated the instances. The consumer
    (Lambda) is not processing.
  - [FAIL] Lambda ReservedConcurrentExecutions: 0 — STEALTH KILL
    SWITCH. The Lambda appears Active in every status check, but
    every invocation is throttled. CloudWatch shows Throttles metric
    spikes (42 in the last 7 days) correlating with interruption
    events. Invocations: 0 — the function has NEVER successfully
    executed.
  - [REVIEW] ALB target group deregistration_delay: 300 seconds
    (default). NOT tuned for Spot — the instance will be terminated
    by EC2 before the ELB finishes draining. Must reduce to 30-60
    seconds.
  - [REVIEW] ASG lifecycle hook: none configured. The ASG does not
    pause for graceful shutdown on Spot termination.
STEPS: (none — pipeline is non-functional; fixes needed first)
POST_VERIFY: (none)
NOTES:
  - Fix 1 (critical): Restore Lambda reserved concurrency:
    aws lambda put-function-concurrency \
      --function-name prod-spot-graceful-shutdown \
      --reserved-concurrent-executions 10
  - Fix 2 (critical): Tune ELB deregistration delay for Spot:
    aws elbv2 modify-target-group-attributes \
      --target-group-arn <tg-arn> \
      --attributes Key=deregistration_delay.timeout_seconds,Value=45
  - Fix 3 (recommended): Add ASG lifecycle hook:
    aws autoscaling put-lifecycle-hook \
      --auto-scaling-group-name prod-api-asg \
      --lifecycle-hook-name spot-termination-hook \
      --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
      --heartbeat-timeout 120 \
      --default-result CONTINUE
  - Fix 4 (recommended): Enable capacity rebalance:
    aws autoscaling update-auto-scaling-group \
      --auto-scaling-group-name prod-api-asg \
      --capacity-rebalance
  - Drain the stale SQS messages after fixing the Lambda — they
    reference already-terminated instances and are no longer actionable.
```

## What the skill caught that a generic assistant misses

1. **Stealth throttle detection.** A generic assistant looks at Lambda
   `State: Active` and concludes the function is healthy. The skill
   checks `get-function-concurrency` separately — reserved concurrency
   = 0 is a stealth kill switch that produces no error logs, only
   Throttles metric spikes.

2. **ELB deregistration delay tuning.** A generic assistant omits that
   the default 300-second delay is too long for Spot. The skill flags
   that the instance will be terminated by EC2 before the ELB finishes
   draining.

3. **2-minute window math.** A generic assistant says "the Lambda
   should handle it." The skill calculates the actual time budget:
   120-second window minus 45-second ELB drain = 75 seconds for
   checkpointing, with a 90-second design target for safety margin.

4. **Capacity rebalance benefit.** A generic assistant omits that
   `CapacityRebalance: true` proactively launches replacements BEFORE
   the 2-minute warning, reducing the effective gap to near-zero.

5. **Checkpoint verification.** A generic assistant omits verifying
   that the checkpoint was actually written. The skill confirms the
   S3 object exists with a timestamp matching the execution.

6. **Diversification awareness.** A generic assistant does not note
   the AZ diversification. The skill highlights that the replacement
   launched in a different AZ, confirming the fleet's diversification
   is working.

7. **3x3 diversification minimum.** A generic assistant does not know
   the 99.9% availability math. The skill references the 3-family x
   3-AZ minimum as the target for production Spot fleets.

## Slash-command invocation

```
/aws:operate-ec2-spot-interruption
```

Or via the orchestrator:

```
/aws:pipeline
You: "handle the Spot interruption warning for i-0abc123def456"
```

The orchestrator emits
`[Phase: Operate | Skills routed: ec2-spot-interruption-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "handle Spot interruption for i-0abc123def456"
# [Phase: Operate | Skills routed: ec2-spot-interruption-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the interruption is handled:

```bash
# Verify the replacement is healthy
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/prod-web-tg/... \
  --targets Id=i-0new456 \
  --profile default

# Verify the Spot Fleet is back to full capacity
aws ec2 describe-spot-fleet-requests \
  --spot-fleet-request-ids sfr-prod-web \
  --query 'SpotFleetRequestConfigs[0].{
    Fulfilled:FulfilledCapacity,
    Target:TargetCapacity,
    Strategy:SpotFleetRequestConfig.AllocationStrategy
  }' \
  --profile default

# Verify the checkpoint exists
aws s3 ls s3://prod-checkpoints/i-0abc123def456/ \
  --profile default

# Check for any Throttles on the Lambda (should be 0)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=prod-spot-shutdown \
  --start-time $(date -u -v-1h +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum \
  --profile default

# Verify the interruption rate is trending down (capacity-optimized)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Usage \
  --metric-name CallCount \
  --dimensions Name=Service,Value=EC2 Name=Resource,Value=Spot \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 --statistics Sum \
  --profile default
```
