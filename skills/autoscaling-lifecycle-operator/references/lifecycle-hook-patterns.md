# Auto Scaling Lifecycle Hook Patterns Reference

Load this reference when planning or executing a lifecycle hook setup. The
patterns below cover the canonical hook configuration, notification target
wiring, Lambda handler structure, and IAM permissions each pattern requires.

## Lifecycle hook configuration matrix

| Lifecycle transition | Typical use | Recommended HeartbeatTimeout | Recommended DefaultResult |
|---|---|---|---|
| `EC2_INSTANCE_LAUNCHING` (launch) | Bootstrap, agent install, config registration, warm-up | 300 (5 min) | CONTINUE (fail-open) |
| `EC2_INSTANCE_LAUNCHING` (launch) | Strict health validation before InService | 300 | ABANDON (replace on failure) |
| `EC2_INSTANCE_TERMINATING` (terminate) | Graceful drain, ELB deregistration, session drain | 300 (5 min) | CONTINUE (proceed with termination) |
| `EC2_INSTANCE_TERMINATING` (terminate) | Spot drain with capacity rebalance | 60-120 | CONTINUE |

## Notification target comparison

| Target | Delivery | Retry | Cost | Best for |
|---|---|---|---|---|
| **Lambda (via EventBridge)** | Direct invocation, < 1s | EventBridge retries up to 3x | Lambda invocations | Most common — direct action execution |
| **SNS topic** | Push to subscriptions (Lambda, HTTP, email) | SNS retries (varies by subscription) | SNS requests + subscription delivery | Fan-out to multiple consumers (drain Lambda + Slack alert + audit log) |
| **SQS queue** | Polling by consumer | SQS visibility timeout + DLQ | SQS requests + retention storage | Decoupled processing, batch drain, consumer-controlled retry |
| **No notification target** | None — instance waits for timeout | N/A | None | Testing (verify the hook fires) or controlled delay |

## EventBridge lifecycle event structure

When a lifecycle hook triggers, Auto Scaling publishes an event to
EventBridge. The event JSON for Lambda and SNS/SQS targets:

```json
{
  "LifecycleActionToken": "c0535863-EXAMPLE",
  "AccountId": "111111111111",
  "LifecycleTransition": "autoscaling:EC2_INSTANCE_LAUNCHING",
  "AutoScalingGroupName": "prod-web-asg",
  "LifecycleHookName": "web-bootstrap-hook",
  "EC2InstanceId": "i-0abc123def456",
  "LifecycleActionSession": "11111111-2222-3333-4444-555555555555",
  "NotificationMetadata": "{\"config_server\": \"https://config.internal\"}",
  "RequestId": "3bc9EXAMPLE",
  "Service": "AWS Auto Scaling",
  "Time": "2026-08-11T03:14:22.000Z"
}
```

The `LifecycleActionToken` is the critical field — without it, the Lambda
cannot call `complete-lifecycle-action`.

## Lambda lifecycle handler skeleton (Python)

```python
import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)
autoscaling = boto3.client('autoscaling')

ASG_NAME = os.environ.get('ASG_NAME', '')
HOOK_NAME = os.environ.get('HOOK_NAME', '')

def lambda_handler(event, context):
    """Handle an Auto Scaling lifecycle event.

    For launch hooks: run bootstrap, then complete-lifecycle-action.
    For terminate hooks: drain traffic, then complete-lifecycle-action.
    """
    logger.info(f"Lifecycle event: {json.dumps(event)}")

    token = event.get('LifecycleActionToken')
    hook_name = event.get('LifecycleHookName', HOOK_NAME)
    asg_name = event.get('AutoScalingGroupName', ASG_NAME)
    instance_id = event.get('EC2InstanceId')
    transition = event.get('LifecycleTransition')

    if not token:
        logger.error("Missing LifecycleActionToken — cannot complete action")
        return {'statusCode': 400, 'body': 'Missing token'}

    try:
        if 'LAUNCHING' in transition:
            # --- LAUNCH: bootstrap the new instance ---
            run_bootstrap(instance_id, event.get('NotificationMetadata'))
        elif 'TERMINATING' in transition:
            # --- TERMINATE: graceful drain ---
            drain_instance(instance_id)

        # Release the instance from the lifecycle wait state
        autoscaling.complete_lifecycle_action(
            LifecycleHookName=hook_name,
            AutoScalingGroupName=asg_name,
            LifecycleActionToken=token,
            LifecycleActionResult='CONTINUE'
        )
        logger.info(f"Completed lifecycle action for {instance_id}")
        return {'statusCode': 200, 'body': 'Lifecycle action completed'}

    except Exception as e:
        logger.error(f"Lifecycle action failed: {e}")
        # Send a heartbeat to extend the timeout while we retry
        try:
            autoscaling.record_lifecycle_action_heartbeat(
                LifecycleHookName=hook_name,
                AutoScalingGroupName=asg_name,
                LifecycleActionToken=token
            )
            logger.info("Heartbeat recorded — instance stays in wait")
        except Exception as hb_err:
            logger.error(f"Heartbeat also failed: {hb_err}")
        raise


def run_bootstrap(instance_id, metadata):
    """Install agents, register with config manager, warm up app."""
    logger.info(f"Bootstrapping instance {instance_id}")
    # Example: trigger SSM Run Command to install the agent
    # ssm = boto3.client('ssm')
    # ssm.send_command(InstanceIds=[instance_id], ...)
    pass


def drain_instance(instance_id):
    """Deregister from ELB, drain active sessions, flush logs."""
    logger.info(f"Draining instance {instance_id}")
    # Example: deregister from target group
    # elbv2 = boto3.client('elbv2')
    # elbv2.deregister_targets(TargetGroupArn=TG_ARN, Targets=[{'Id': instance_id}])
    # Wait for deregistration delay
    pass
```

## IAM permissions for lifecycle Lambdas

**Lambda execution role identity-based policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "autoscaling:CompleteLifecycleAction",
        "autoscaling:RecordLifecycleActionHeartbeat"
      ],
      "Resource": "arn:aws:autoscaling:*:*:autoScalingGroup:*:autoScalingGroupName/prod-*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

For terminate hooks with ELB deregistration, add:

```json
{
  "Effect": "Allow",
  "Action": [
    "elasticloadbalancing:DeregisterTargets",
    "elasticloadbalancing:DescribeTargetHealth"
  ],
  "Resource": "arn:aws:elasticloadbalancing:*:*:targetgroup/*/*"
}
```

**EventBridge rule for lifecycle events:**

```json
{
  "source": ["aws.autoscaling"],
  "detail-type": ["EC2 Instance-launch Lifecycle Action", "EC2 Instance-terminate Lifecycle Action"],
  "detail": {
    "AutoScalingGroupName": ["prod-web-asg"]
  }
}
```

## SNS notification target setup

When using SNS as the notification target, the ASG service-linked role
publishes to the topic. Ensure:

1. The topic exists and has at least one confirmed subscription.
2. The topic policy allows `Service: autoscaling.amazonaws.com` to publish:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "autoscaling.amazonaws.com"},
    "Action": "SNS:Publish",
    "Resource": "arn:aws:sns:us-east-1:111111111111:lifecycle-notifications"
  }]
}
```

3. The `--role-arn` on `put-lifecycle-hook` points to the ASG service-
   linked role (`AWSServiceRoleForAutoScaling`).

## SQS notification target setup

When using SQS, the ASG service-linked role sends to the queue:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "autoscaling.amazonaws.com"},
    "Action": "sqs:SendMessage",
    "Resource": "arn:aws:sqs:us-east-1:111111111111:lifecycle-queue"
  }]
}
```

Set the queue visibility timeout >= HeartbeatTimeout to prevent duplicate
processing. Configure a DLQ for failed lifecycle actions.

## Multiple hooks on the same transition

Multiple launch or terminate hooks fire in the order they were created.
Each hook must be completed (via `complete-lifecycle-action` or timeout)
before the next hook fires. The total transition time is the sum of all
HeartbeatTimeouts.

Example: two launch hooks with 300s each = up to 600s in `Pending:Wait`.

```
Pending:Wait (hook1, 300s) -> Pending:Wait (hook2, 300s) -> InService
```

Use `describe-lifecycle-hooks` to list all hooks and their order.

## Warm pool + lifecycle hook interaction

When a warm pool instance is claimed by the ASG on scale-out:

1. Instance transitions from `Stopped` (warm pool) to `Running`.
2. Instance enters `Pending:Wait` — the launch lifecycle hook fires.
3. The hook Lambda receives the event. The instance already has the OS
   booted (warm pool pre-booted it), so the Lambda should skip AMI-level
   bootstrap and run only app-level initialization.
4. Lambda calls `complete-lifecycle-action` -> instance enters `InService`.

The Lambda can detect warm-pool-sourced instances by checking if the
instance was recently in `Stopped` state (via `describe-instances` or
a tag set during warm pool initialization).

## Capacity rebalance + terminate hook timing

```
Spot Rebalance Recommendation
  |
  v
ASG launches replacement instance (immediately)
  |
  v
ASG puts old instance into Terminating:Wait
  |
  v
Terminate hook fires (HeartbeatTimeout countdown begins)
  |
  +-- Lambda drains traffic, deregisters from ELB
  |
  v
Lambda calls complete-lifecycle-action (or HeartbeatTimeout expires)
  |
  v
Instance terminated

--- Meanwhile ---
Spot 2-minute interruption notice (may arrive 0-2 min after rebalance)
  |
  v
Force termination (hook cannot prevent this)
```

The terminate hook must complete BEFORE the 2-minute interruption notice
force-terminates the instance. With capacity rebalance, the rebalance
recommendation gives a head start (often 30-120 seconds before the
interruption notice). Set HeartbeatTimeout to 60-120 for Spot ASGs.

## CLI quick-reference

| Goal | Command |
|---|---|
| List hooks | `aws autoscaling describe-lifecycle-hooks --auto-scaling-group-name <asg>` |
| Add launch hook | `aws autoscaling put-lifecycle-hook --lifecycle-hook-name <name> --auto-scaling-group-name <asg> --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING --heartbeat-timeout 300 --default-result CONTINUE` |
| Add terminate hook | `aws autoscaling put-lifecycle-hook --lifecycle-hook-name <name> --auto-scaling-group-name <asg> --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING --heartbeat-timeout 300 --default-result CONTINUE` |
| Complete action | `aws autoscaling complete-lifecycle-action --lifecycle-hook-name <hook> --auto-scaling-group-name <asg> --lifecycle-action-token <token> --lifecycle-action-result CONTINUE` |
| Send heartbeat | `aws autoscaling record-lifecycle-action-heartbeat --lifecycle-hook-name <hook> --auto-scaling-group-name <asg> --lifecycle-action-token <token>` |
| Delete hook | `aws autoscaling delete-lifecycle-hook --auto-scaling-group-name <asg> --lifecycle-hook-name <name>` |
| Describe warm pool | `aws autoscaling describe-warm-pool --auto-scaling-group-name <asg>` |
| Configure warm pool | `aws autoscaling put-warm-pool --auto-scaling-group-name <asg> --pool-min-size 3 --max-group-prepared-capacity 5` |
| Set instance protection | `aws autoscaling set-instance-protection --instance-ids <i-xxx> --auto-scaling-group-name <asg> --protected-from-scale-in` |
| Enter standby | `aws autoscaling enter-standby --instance-ids <i-xxx> --auto-scaling-group-name <asg> --should-decrement-desired-capacity` |
| Exit standby | `aws autoscaling exit-standby --instance-ids <i-xxx> --auto-scaling-group-name <asg>` |
| Add scheduled action | `aws autoscaling put-scheduled-action --auto-scaling-group-name <asg> --scheduled-action-name <name> --recurrence "cron(0 9 * * MON-FRI *)" --min-size 2 --max-size 20 --desired-capacity 5` |
| Add target tracking policy | `aws autoscaling put-scaling-policy --auto-scaling-group-name <asg> --policy-name <name> --policy-type TargetTrackingScaling --target-tracking-configuration ...` |
| Enable capacity rebalance | `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <asg> --capacity-rebalance` |
