# End-to-end usage scenario: autoscaling-lifecycle-operator

A walkthrough showing the skill planning an add-launch-hook operation on
a web-tier ASG with bootstrap registration Lambda, all pre-checks
passing, and the operator confirming at the CONFIRM gate. Contrasted
with the REVIEW_REQUIRED case where a terminate hook with HeartbeatTimeout
3600 is rejected on a Spot ASG with capacity rebalance.

## Input (user prompt)

> We have a web-tier ASG `prod-web-asg` and we want to add a launch
> lifecycle hook `web-bootstrap-hook` that triggers the Lambda
> `web-lifecycle-action` to install the CloudWatch agent and register
> with our config server. HeartbeatTimeout 300s, DefaultResult CONTINUE.

```json
{
  "Operation": "add-launch-hook",
  "ASG": "prod-web-asg",
  "HookName": "web-bootstrap-hook",
  "HeartbeatTimeout": 300,
  "DefaultResult": "CONTINUE",
  "NotificationTarget": "arn:aws:lambda:us-east-1:111111111111:function:web-lifecycle-action",
  "AsgMetadata": {
    "MinSize": 2,
    "MaxSize": 20,
    "DesiredCapacity": 4,
    "LaunchTemplate": {"LaunchTemplateId": "lt-abc123", "Version": "2"},
    "HealthCheckType": "ELB",
    "HealthCheckGracePeriod": 600
  },
  "LambdaMetadata": {
    "State": "Active",
    "Timeout": 120
  },
  "LambdaRolePolicies": [
    "AWSLambdaBasicExecutionRole",
    "autoscaling:CompleteLifecycleAction on arn:aws:autoscaling:us-east-1:111111111111:autoScalingGroup:..."
  ]
}
```

## Skill output

```text
OPERATION: add-launch-hook
VERDICT: OPERATION_COMPLETED
TARGET: prod-web-asg (hook: web-bootstrap-hook)
PRE_CHECKS:
  - [PASS] ASG exists, DesiredCapacity: 4, MaxSize: 20
  - [PASS] No existing hook named web-bootstrap-hook
  - [PASS] HeartbeatTimeout: 300 (in [30, 7200])
  - [PASS] DefaultResult: CONTINUE
  - [PASS] Lambda web-lifecycle-action State: Active, Timeout: 120
  - [PASS] Lambda role has autoscaling:CompleteLifecycleAction
  - [PASS] HealthCheckGracePeriod: 600 >= bootstrap duration 120s
STEPS:
  1. CONFIRM: About to add launch lifecycle hook web-bootstrap-hook
     on prod-web-asg with HeartbeatTimeout 300s, DefaultResult CONTINUE,
     Lambda web-lifecycle-action, in account 111111111111 region
     us-east-1. New instances will enter Pending:Wait for up to 300s.
     Proceed? (yes/no)
  2. aws autoscaling put-lifecycle-hook \
       --lifecycle-hook-name web-bootstrap-hook \
       --auto-scaling-group-name prod-web-asg \
       --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
       --heartbeat-timeout 300 \
       --default-result CONTINUE \
       --notification-target-arn arn:aws:lambda:us-east-1:111111111111:function:web-lifecycle-action
POST_VERIFY:
  - [PASS] describe-lifecycle-hooks: web-bootstrap-hook active
  - [PASS] Test scale-out: instance entered Pending:Wait, Lambda invoked,
    instance transitioned to InService in 87s
NOTES:
  - The Lambda receives EventBridge events on EC2 Instance-launch
    Lifecycle Action. It runs bootstrap and calls
    complete-lifecycle-action with CONTINUE.
  - If the Lambda crashes, the instance stays in Pending:Wait for
    300s, then DefaultResult CONTINUE fires.
```

## Contrast — REVIEW_REQUIRED case (Spot ASG, timeout too long)

If the operator had specified HeartbeatTimeout 3600 on a Spot ASG with
capacity rebalance, the pre-check gate would fire:

```text
OPERATION: add-terminate-hook
VERDICT: REVIEW_REQUIRED
TARGET: prod-spot-asg
PRE_CHECKS:
  - [PASS] ASG exists with MixedInstancesPolicy (Spot)
  - [PASS] No existing hook named spot-drain-hook
  - [FAIL] HeartbeatTimeout: 3600 exceeds the Spot 2-minute
    interruption window. With capacity rebalance enabled, the
    terminate hook must complete within 60-120 seconds before the
    Spot interruption force-terminates the instance.
STEPS: (none — pre-checks failed)
NOTES:
  - Fix: reduce HeartbeatTimeout to 90s:
    put-lifecycle-hook --heartbeat-timeout 90
```

## What the skill caught that a generic assistant misses

1. **HeartbeatTimeout validation against Spot constraints.** A generic
   assistant accepts 3600s without checking if the ASG uses Spot. The
   skill detects capacity rebalance + Spot and rejects timeouts > 120s.

2. **Lambda complete-lifecycle-action IAM check.** A generic assistant
   adds the hook without verifying the Lambda can call
   complete-lifecycle-action. The skill checks the Lambda execution role.

3. **HealthCheckGracePeriod compatibility.** A generic assistant omits
   the ELB grace period check. The skill ensures the hook completes
   before the grace period expires.

4. **Warm pool + hook interaction.** A generic assistant does not mention
   that warm pool instances also trigger the launch hook. The skill
   surfaces this so the Lambda can be designed accordingly.

5. **Multiple hook stacking.** A generic assistant does not calculate
   the total transition time. The skill flags when multiple hooks would
   create excessive wait.

6. **Stuck-instance diagnostics.** A generic assistant does not provide
   the failure-mode table or the manual complete-lifecycle-action
   override. The skill includes the full diagnostic path.

## Slash-command invocation

```
/aws:operate-autoscaling-lifecycle
```

## CLI routing

```bash
node cli/bin/cli.js route "add launch hook on prod-web-asg"
# [Phase: Operate | Skills routed: autoscaling-lifecycle-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After adding the hook, verify with a test scale-out:

```bash
# Trigger a scale-out
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name prod-web-asg \
  --desired-capacity 5 \
  --profile default

# Watch the new instance enter Pending:Wait and the Lambda fire
aws logs tail /aws/lambda/web-lifecycle-action --follow --since 5m \
  --profile default

# Verify the instance transitioned to InService
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names prod-web-asg \
  --query 'AutoScalingGroups[0].Instances[*].[InstanceId,LifecycleState]' \
  --profile default
```
