# Auto Scaling Lifecycle Hook Diagnostic Procedures Reference

Load this reference when diagnosing a stuck lifecycle instance or a
malfunctioning lifecycle hook. The procedures below are the canonical
sequences for each symptom archetype, with read-only diagnostic commands
and the CLI to fix each root cause.

## Decision tree — which diagnostic archetype

| Symptom | Use | Why |
|---|---|---|
| Instance in `Pending:Wait` beyond HeartbeatTimeout | **Stuck launch** | Lambda never called complete-lifecycle-action |
| Instance in `Terminating:Wait` beyond HeartbeatTimeout | **Stuck terminate** | Same as above for terminate hook |
| Instance in `Pending:Wait`, Lambda never invoked | **No delivery** | EventBridge rule missing or SNS subscription unconfirmed |
| Instance in `Pending:Wait`, Lambda errored | **Lambda failure** | Timeout, IAM denied, or code error |
| Instance terminated despite terminate hook | **Spot force-kill** | HeartbeatTimeout > Spot 2-min window |
| Warm pool not growing to MinSize | **Warm pool issue** | Subnet IP exhaustion, vCPU quota, or launch template error |
| Scale-out slower than expected | **Hook latency** | HeartbeatTimeout too long or Lambda slow |
| `put-lifecycle-hook` returns `ValidationError` | **Invalid params** | HeartbeatTimeout outside 30-7200 or malformed ARN |
| Multiple hooks, long wait | **Hook stacking** | Each hook adds its HeartbeatTimeout to the total |

## Procedure: Stuck launch (instance in Pending:Wait)

**Symptom:** Instance in `Pending:Wait` state for longer than
HeartbeatTimeout, or longer than expected.

**Diagnostics:**

```bash
# 1. Identify stuck instances
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <asg> \
  --query 'AutoScalingGroups[0].Instances[?LifecycleState==`Pending:Wait`].[InstanceId,LifecycleState]'

# 2. Check the hook configuration
aws autoscaling describe-lifecycle-hooks \
  --auto-scaling-group-name <asg> \
  --query 'LifecycleHooks[?LifecycleTransition==`autoscaling:EC2_INSTANCE_LAUNCHING`]'

# 3. Check Lambda invocations and errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/<lifecycle-lambda> \
  --filter-pattern ERROR \
  --start-time $(($(date +%s) - 3600))000 \
  --limit 20

# 4. Check Lambda timeout vs bootstrap duration
aws lambda get-function-configuration \
  --function-name <lifecycle-lambda> \
  --query '{Timeout:Timeout,State:State}'

# 5. Check EventBridge rule for lifecycle events
aws events list-rules \
  --name-prefix <rule-prefix> \
  --query 'Rules[?contains(EventPattern, `EC2 Instance-launch Lifecycle Action`)]'
```

**Common findings and fixes:**

| Finding | Fix |
|---|---|
| Lambda `Task timed out after X seconds` | `aws lambda update-function-configuration --function-name <lambda> --timeout 120` |
| Lambda `AccessDenied` on `CompleteLifecycleAction` | Add `autoscaling:CompleteLifecycleAction` to the Lambda execution role |
| EventBridge rule missing | Create a rule matching `EC2 Instance-launch Lifecycle Action` targeting the Lambda |
| SNS subscription `PendingConfirmation` | Confirm the subscription (email click or Lambda API) |
| HeartbeatTimeout too long (3600s default) | `put-lifecycle-hook` with `--heartbeat-timeout 300` |
| Lambda never invoked, no errors | EventBridge rule not targeting the Lambda, or rule pattern mismatch |

**Manual override — force complete the stuck instance:**

```bash
# Get the lifecycle action token from EventBridge or CloudTrail
aws autoscaling complete-lifecycle-action \
  --lifecycle-hook-name <hook> \
  --auto-scaling-group-name <asg> \
  --lifecycle-action-token <token> \
  --lifecycle-action-result CONTINUE
```

If you don't have the token, find it in CloudTrail:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=EC2_INSTANCE_LAUNCHING \
  --max-results 10
```

## Procedure: Stuck terminate (instance in Terminating:Wait)

**Symptom:** Instance in `Terminating:Wait` beyond HeartbeatTimeout.

**Diagnostics:** Same as stuck launch, but filter for
`EC2_INSTANCE_TERMINATING` and check the terminate hook Lambda.

**Additional checks:**

```bash
# Check ELB target group deregistration delay
aws elbv2 describe-target-group-attributes \
  --target-group-arn <tg-arn> \
  --query 'Attributes[?Key==`deregistration_delay.timeout_seconds`]'

# If deregistration delay > HeartbeatTimeout, the instance is terminated
# before drain completes. Fix by increasing HeartbeatTimeout or decreasing
# the deregistration delay.
```

## Procedure: Spot force-kill (instance terminated despite hook)

**Symptom:** Instance terminated despite a terminate hook. CloudTrail
shows the Spot interruption notice within 2 minutes of the rebalance
recommendation.

**Root cause:** HeartbeatTimeout was set too high (e.g., 3600s). The Spot
2-minute interruption notice force-terminates the instance regardless of
the hook state.

**Fix:**

```bash
# Reduce HeartbeatTimeout to 60-120s for Spot ASGs
aws autoscaling put-lifecycle-hook \
  --lifecycle-hook-name <hook> \
  --auto-scaling-group-name <asg> \
  --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
  --heartbeat-timeout 90 \
  --default-result CONTINUE \
  --notification-target-arn <lambda-arn>
```

## Procedure: Warm pool not growing

**Symptom:** `describe-warm-pool` shows fewer instances than `PoolMinSize`.

**Diagnostics:**

```bash
# 1. Check warm pool state
aws autoscaling describe-warm-pool \
  --auto-scaling-group-name <asg> \
  --query '{PoolMinSize:PoolMinSize,MaxGroupPreparedCapacity:MaxGroupPreparedCapacity,Instances:Instances[*].[InstanceId,LifecycleState]}'

# 2. Check for failed launches
aws ec2 describe-instances \
  --filters "Name=tag:aws:autoscaling:groupName,Values=<asg>" \
  --query 'Reservations[*].Instances[?State.Name==`terminated`].[InstanceId,StateReason.Message]'

# 3. Check subnet IP availability
aws ec2 describe-subnets \
  --subnet-ids <subnet-1> <subnet-2> \
  --query 'Subnets[*].[SubnetId,AvailableIpAddressCount]'

# 4. Check vCPU quota (running + stopped on-demand instances)
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-1216C47A

# 5. Check launch template validity
aws ec2 describe-launch-template-versions \
  --launch-template-id <lt-id> \
  --versions <version>
```

**Common findings:**

| Finding | Fix |
|---|---|
| Subnet IP exhaustion | Add more subnets to the ASG or free up IPs |
| vCPU quota exceeded | Request a quota increase |
| Launch template references deleted AMI | Update the launch template with a valid AMI |
| Instance type unavailable in AZ | Update the ASG subnets or instance type |
| Warm pool MaxGroupPreparedCapacity < PoolMinSize | Fix the configuration (invalid) |

## Procedure: Lambda IAM denial on complete-lifecycle-action

**Symptom:** Lambda CloudWatch logs show `AccessDeniedException` on
`CompleteLifecycleAction`.

**Diagnostic:**

```bash
# Check the Lambda execution role policy
aws iam list-attached-role-policies --role-name <role>
aws iam list-role-policies --role-name <role>

# Look for autoscaling:CompleteLifecycleAction in the policies
aws iam get-role-policy --role-name <role> --policy-name <policy-name>
```

**Fix:**

```bash
# Attach a policy granting complete-lifecycle-action
aws iam put-role-policy \
  --role-name <role> \
  --policy-name lifecycle-complete \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "autoscaling:CompleteLifecycleAction",
        "autoscaling:RecordLifecycleActionHeartbeat"
      ],
      "Resource": "arn:aws:autoscaling:*:*:autoScalingGroup:*:autoScalingGroupName/<asg>"
    }]
  }'
```

## Procedure: EventBridge rule missing or misconfigured

**Symptom:** Lifecycle hook is configured, instances enter `Pending:Wait`,
but the Lambda is never invoked.

**Diagnostic:**

```bash
# List EventBridge rules for the ASG
aws events list-rules --name-prefix "autoscaling-"

# Check if the rule targets the Lambda
aws events list-targets-by-rule --rule <rule-name>

# Check the rule pattern (must match the lifecycle detail type)
aws events describe-rule --name <rule-name> --query 'EventPattern'
```

**Fix:**

```bash
# Create the EventBridge rule
aws events put-rule \
  --name lifecycle-launch-<asg> \
  --event-pattern '{
    "source": ["aws.autoscaling"],
    "detail-type": ["EC2 Instance-launch Lifecycle Action"],
    "detail": {"AutoScalingGroupName": ["<asg>"]}
  }'

# Add the Lambda as target
aws events put-targets \
  --rule lifecycle-launch-<asg> \
  --targets '[{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:111111111111:function:<lambda>"}]'

# Add Lambda permission for EventBridge
aws lambda add-permission \
  --function-name <lambda> \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:111111111111:rule/lifecycle-launch-<asg>
```

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| ASG state | `aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <asg>` |
| Lifecycle hooks | `aws autoscaling describe-lifecycle-hooks --auto-scaling-group-name <asg>` |
| Warm pool | `aws autoscaling describe-warm-pool --auto-scaling-group-name <asg>` |
| Scaling policies | `aws autoscaling describe-scaling-policies --auto-scaling-group-name <asg>` |
| Scheduled actions | `aws autoscaling describe-scheduled-actions --auto-scaling-group-name <asg>` |
| Instance lifecycle state | `aws autoscaling describe-auto-scaling-groups --asg-names <asg> --query 'AutoScalingGroups[0].Instances[*].[InstanceId,LifecycleState]'` |
| Lambda logs | `aws logs filter-log-events --log-group-name /aws/lambda/<lambda> --filter-pattern ERROR --limit 20` |
| Lambda configuration | `aws lambda get-function-configuration --function-name <lambda>` |
| Lambda role policies | `aws iam list-attached-role-policies --role-name <role>` + `aws iam list-role-policies --role-name <role>` |
| EventBridge rules | `aws events list-rules --name-prefix autoscaling-` |
| ELB target health | `aws elbv2 describe-target-health --target-group-arn <tg>` |
| Target group attributes | `aws elbv2 describe-target-group-attributes --target-group-arn <tg>` |
| Instance status | `aws ec2 describe-instance-status --instance-ids <i-xxx>` |
| CloudTrail lifecycle events | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=EC2_INSTANCE_LAUNCHING` |
| Force complete action | `aws autoscaling complete-lifecycle-action --lifecycle-hook-name <hook> --auto-scaling-group-name <asg> --lifecycle-action-token <token> --lifecycle-action-result CONTINUE` |
| Extend timeout | `aws autoscaling record-lifecycle-action-heartbeat --lifecycle-hook-name <hook> --auto-scaling-group-name <asg> --lifecycle-action-token <token>` |

## Failure-mode to operation routing

| Failure mode | Recommended operation | Notes |
|---|---|---|
| Instance stuck in `Pending:Wait` | diagnose-stuck | Check Lambda logs first, then force complete |
| Instance stuck in `Terminating:Wait` | diagnose-stuck | Check Lambda + ELB deregistration delay |
| Lambda never invoked | diagnose-stuck | EventBridge rule or SNS subscription issue |
| Spot instance killed despite hook | modify-hook | Reduce HeartbeatTimeout to 60-120s |
| Warm pool not growing | configure-warm-pool | Check subnet IPs, vCPU quota, AMI validity |
| Scale-out too slow | modify-hook | Reduce HeartbeatTimeout or optimize Lambda |
| Multiple hooks stacking | modify-hook | Consolidate or reduce HeartbeatTimeouts |
