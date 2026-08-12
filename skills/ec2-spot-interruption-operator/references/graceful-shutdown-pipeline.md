# EC2 Spot Instance Graceful Shutdown Pipeline Reference

Load this reference when configuring or auditing the Spot Instance
interruption graceful-shutdown pipeline. The components below cover the
EventBridge rule, SQS queue, Lambda function, ELB deregistration, ASG
lifecycle hooks, and the checkpointing patterns.

## Pipeline architecture

```
EC2 Spot Interruption Warning
        |
        v
EventBridge Rule (ENABLED)
        |
        v
SQS Queue (with DLQ)  <-- or direct Lambda target
        |
        v
Lambda: prod-spot-graceful-shutdown
   |         |          |
   v         v          v
ELB        SSM         S3 / DynamoDB
Deregister  SIGTERM    Checkpoint
```

Total budget: 120 seconds (2-minute warning). Design for 90 seconds to
leave a safety margin.

## Component 1: EventBridge rule

The rule matches the `EC2 Spot Instance Interruption Warning` event.

```bash
aws events put-rule \
  --name spot-interruption-warning \
  --event-pattern '{
    "detail-type": ["EC2 Spot Instance Interruption Warning"],
    "source": ["aws.ec2"]
  }'
```

### Event payload structure

```json
{
  "version": "0",
  "id": "12345678-1234-1234-1234-123456789012",
  "detail-type": "EC2 Spot Instance Interruption Warning",
  "source": "aws.ec2",
  "account": "111111111111",
  "time": "2026-08-11T14:23:00Z",
  "region": "us-east-1",
  "resources": ["arn:aws:ec2:us-east-1:111111111111:instance/i-0abc123def456"],
  "detail": {
    "instance-id": "i-0abc123def456",
    "instance-action": "terminate"
  }
}
```

The `instance-action` field is one of: `terminate`, `stop`, `hibernate`.

### Targets

The rule can target an SQS queue (recommended for buffering and retry)
or a Lambda function directly. The SQS queue approach decouples the
event delivery from the processing, which is safer under high-
interruption scenarios.

```bash
# Target: SQS queue
aws events put-targets \
  --rule spot-interruption-warning \
  --targets '[{"Id":"1","Arn":"arn:aws:sqs:us-east-1:111111111111:spot-interruption-queue"}]'

# OR target: Lambda function directly
aws events put-targets \
  --rule spot-interruption-warning \
  --targets '[{"Id":"1","Arn":"arn:aws:lambda:us-east-1:111111111111:function:prod-spot-graceful-shutdown"}]'
```

For direct Lambda targets, add the resource-based policy:

```bash
aws lambda add-permission \
  --function-name prod-spot-graceful-shutdown \
  --statement-id EventBridgeInvoke \
  --principal events.amazonaws.com \
  --action lambda:InvokeFunction \
  --source-arn arn:aws:events:us-east-1:111111111111:rule:spot-interruption-warning
```

## Component 2: SQS queue (interruption queue)

```bash
# Create the queue
aws sqs create-queue --queue-name spot-interruption-queue

# Create the dead-letter queue
aws sqs create-queue --queue-name spot-interruption-dlq

# Configure the redrive policy (DLQ)
QUEUE_URL=$(aws sqs get-queue-url --queue-name spot-interruption-queue --query 'QueueUrl' --output text)
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url $(aws sqs get-queue-url --queue-name spot-interruption-dlq --query 'QueueUrl' --output text) --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"3\"}"
```

### Queue health thresholds

| Metric | Healthy | Warning | Critical |
|---|---|---|---|
| `ApproximateNumberOfMessagesVisible` | 0-5 | 6-20 | > 20 (consumer lag) |
| `ApproximateAgeOfOldestMessage` | < 60s | 60-120s | > 120s (stale — instance already terminated) |
| DLQ message count | 0 | 1-3 | > 3 (repeated processing failures) |

### CloudWatch alarms for queue health

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name spot-queue-depth-high \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=spot-interruption-queue \
  --threshold 10 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 --evaluation-periods 1 \
  --alarm-actions <sns-topic-arn>

aws cloudwatch put-metric-alarm \
  --alarm-name spot-queue-oldest-message-stale \
  --namespace AWS/SQS \
  --metric-name ApproximateAgeOfOldestMessage \
  --dimensions Name=QueueName,Value=spot-interruption-queue \
  --threshold 120 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 --evaluation-periods 1 \
  --alarm-actions <sns-topic-arn>
```

## Component 3: Lambda graceful-shutdown function

### Skeleton (Python)

```python
import boto3
import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
elbv2 = boto3.client('elasticloadbalancing')
s3 = boto3.client('s3')
ssm = boto3.client('ssm')

CHECKPOINT_BUCKET = os.environ.get('CHECKPOINT_BUCKET', 'prod-checkpoints')
TARGET_GROUP_ARNS = json.loads(os.environ.get('TARGET_GROUP_ARNS', '[]'))

def lambda_handler(event, context):
    """Handle a Spot Instance Interruption Warning."""
    detail = event.get('detail', {})
    instance_id = detail.get('instance-id')
    instance_action = detail.get('instance-action', 'terminate')

    if not instance_id:
        logger.error("No instance-id in event")
        return {'statusCode': 400, 'body': 'No instance-id'}

    logger.info(f"Handling {instance_action} for {instance_id}")

    # Step 1: Deregister from all target groups (drain from ELB)
    for tg_arn in TARGET_GROUP_ARNS:
        try:
            elbv2.deregister_targets(
                TargetGroupArn=tg_arn,
                Targets=[{'Id': instance_id}]
            )
            logger.info(f"Deregistered {instance_id} from {tg_arn}")
        except Exception as e:
            logger.warning(f"Deregister failed for {tg_arn}: {e}")

    # Step 2: Signal the application to flush and checkpoint
    try:
        ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [
                'systemctl stop my-application || true',
                f'aws s3 cp /var/lib/myapp/state.json '
                f's3://{CHECKPOINT_BUCKET}/{instance_id}/state.json || true'
            ]},
            TimeoutSeconds=60
        )
        logger.info(f"Sent checkpoint signal to {instance_id}")
    except Exception as e:
        logger.warning(f"SSM command failed: {e}")

    # Step 3: Write a pipeline checkpoint (for auditing)
    try:
        s3.put_object(
            Bucket=CHECKPOINT_BUCKET,
            Key=f'pipeline/{instance_id}/{context.aws_request_id}.json',
            Body=json.dumps({
                'instance_id': instance_id,
                'action': instance_action,
                'event_time': event.get('time'),
                'processed_at': context.get_remaining_time_in_millis()
            })
        )
    except Exception as e:
        logger.warning(f"Pipeline checkpoint failed: {e}")

    return {
        'statusCode': 200,
        'body': f'Handled {instance_action} for {instance_id}'
    }
```

### Lambda configuration

| Setting | Recommended value | Reason |
|---|---|---|
| Timeout | 90 seconds | Must complete within the 2-minute window with a safety margin |
| Memory | 256 MB | Lightweight API calls; increase if checkpointing large state |
| Reserved concurrency | >= 5 | Guarantees the function can execute even under account-wide Lambda load; NEVER 0 |
| Runtime | python3.12 | Latest supported runtime |
| IAM role | See below | Least-privilege permissions |

### Lambda execution role permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:DescribeInstances"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DeregisterTargets",
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:DescribeTargetGroups"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::prod-checkpoints/*"
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:SendCommand"],
      "Resource": [
        "arn:aws:ssm:*:*:document/AWS-RunShellScript",
        "arn:aws:ec2:*:*:instance/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Component 4: ELB target group configuration

```bash
# Set the deregistration delay to 30-60 seconds for Spot targets
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes Key=deregistration_delay.timeout_seconds,Value=45
```

The deregistration delay must fit within the 2-minute window, leaving
time for checkpointing. Recommended: 30-60 seconds.

| Setting | Value for Spot targets | Reason |
|---|---|---|
| `deregistration_delay.timeout_seconds` | 30-60 | Must drain before the 2-minute window expires |
| Health check interval | 10 seconds | Faster detection of healthy replacements |
| Healthy threshold | 2 | Faster registration of replacements |
| Unhealthy threshold | 2 | Faster deregistration of failing targets |

## Component 5: ASG lifecycle hooks

```bash
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name prod-web-asg \
  --lifecycle-hook-name spot-termination-hook \
  --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
  --heartbeat-timeout 120 \
  --default-result CONTINUE
```

The lifecycle hook places the instance in `Terminating:Wait` when the
Spot interruption triggers termination. The `HeartbeatTimeout` should
be 120 seconds (matching the 2-minute window). The `DefaultResult` of
`CONTINUE` means the ASG proceeds with termination after the timeout
even if the hook does not complete — this is correct for Spot (the
instance is being terminated by EC2 regardless).

## Component 6: Checkpointing patterns

### S3 checkpoint (for file-based state)

```python
# In the application (on SIGTERM handler):
import signal
import boto3
import json
import os

s3 = boto3.client('s3')
CHECKPOINT_BUCKET = os.environ['CHECKPOINT_BUCKET']

def checkpoint(signum, frame):
    state = collect_application_state()
    s3.put_object(
        Bucket=CHECKPOINT_BUCKET,
        Key=f'{os.environ["HOSTNAME"]}/state.json',
        Body=json.dumps(state)
    )
    os._exit(0)

signal.signal(signal.SIGTERM, checkpoint)
```

### DynamoDB checkpoint (for session or cursor state)

```python
# In the application (on SIGTERM handler):
import signal
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CHECKPOINT_TABLE'])

def checkpoint(signum, frame):
    cursor = get_processing_cursor()
    table.put_item(
        Item={
            'worker_id': os.environ['HOSTNAME'],
            'cursor': cursor,
            'timestamp': int(time.time())
        }
    )
    os._exit(0)

signal.signal(signal.SIGTERM, checkpoint)
```

### Checkpoint restore (on replacement startup)

```python
# On application startup, attempt to restore from the latest checkpoint
def restore_from_checkpoint():
    try:
        response = s3.get_object(
            Bucket=CHECKPOINT_BUCKET,
            Key=f'{previous_instance_id}/state.json'
        )
        state = json.loads(response['Body'].read())
        resume_from_state(state)
    except s3.exceptions.NoSuchKey:
        logger.info("No checkpoint found — starting fresh")
```

## Synthetic test

Test the pipeline with a synthetic EventBridge event before relying on
it for a real interruption:

```bash
# Emit a synthetic event (use a NON-PRODUCTION instance ID)
aws events put-events \
  --entries '[{
    "EventBusName": "default",
    "Source": "aws.ec2",
    "DetailType": "EC2 Spot Instance Interruption Warning",
    "Detail": "{\"instance-id\":\"i-test123\",\"instance-action\":\"terminate\"}",
    "Resources": ["arn:aws:ec2:us-east-1:111111111111:instance/i-test123"]
  }]'

# Verify the Lambda executed
aws logs tail /aws/lambda/prod-spot-graceful-shutdown --since 2m

# Verify the checkpoint was written
aws s3 ls s3://prod-checkpoints/i-test123/
```

## Common failure signatures

| Symptom | Root cause | Fix |
|---|---|---|
| Lambda never invoked | Reserved concurrency = 0 OR resource-based policy missing | `put-function-concurrency --reserved-concurrent-executions 5`; add `lambda:InvokeFunction` permission |
| Lambda timed out | Timeout < 60s OR checkpoint write slow | `update-function-configuration --timeout 90`; optimize checkpoint |
| Instance not deregistered | Lambda lacks `elasticloadbalancing:DeregisterTargets` | Add the permission to the Lambda role |
| ELB still sending traffic after deregister | `deregistration_delay.timeout_seconds` > 120 | Modify target group attributes to 30-60 seconds |
| Checkpoint not written | Lambda lacks `s3:PutObject` OR S3 bucket missing | Add permission; verify bucket exists |
| SQS queue depth climbing | Lambda consumer lagging | Increase reserved concurrency; investigate Lambda errors |
| No events at all | EventBridge rule disabled OR wrong event pattern | Verify rule `State: ENABLED`; verify event pattern matches |
