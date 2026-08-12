# Targets, IAM, and Error Handling — EventBridge Scheduler Deployer

Deep reference on target types and their specific configurations,
IAM role mechanics (Scheduler-managed roles, iam:PassRole
requirement, per-target-type permissions), schedule groups (bulk
enable/disable, group lifecycle), retry policy and dead-letter queue
(error handling, exponential backoff, DLQ message processing), and
CloudWatch metrics for monitoring. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Target types

### Supported targets

EventBridge Scheduler supports 200+ AWS target types through universal
templates. The most common:

| Target type | ARN example | Action | Role permission needed |
|---|---|---|---|
| Lambda | `arn:aws:lambda:<r>:<a>:function:<n>` | Invoke | `lambda:InvokeFunction` |
| Step Functions | `arn:aws:states:<r>:<a>:stateMachine:<n>` | StartExecution | `states:StartExecution` |
| SNS | `arn:aws:sns:<r>:<a>:<n>` | Publish | `sns:Publish` |
| SQS | `arn:aws:sqs:<r>:<a>:<n>` | SendMessage | `sqs:SendMessage` |
| Kinesis | `arn:aws:kinesis:<r>:<a>:stream/<n>` | PutRecord | `kinesis:PutRecord` |
| CodeBuild | `arn:aws:codebuild:<r>:<a>:project/<n>` | StartBuild | `codebuild:StartBuild` |
| ECS | `arn:aws:ecs:<r>:<a>:...` | RunTask | `ecs:RunTask` |
| CodePipeline | `arn:aws:codepipeline:<r>:<a>:...` | StartExecution | `codepipeline:StartPipelineExecution` |
| Inspector | `arn:aws:inspector2:<r>:<a>:...` | Various | Inspector-specific |
| Bedrock | `arn:aws:bedrock:<r>:<a>:...` | InvokeModel | Bedrock-specific |

### Target configuration structure

```json
{
  "RoleArn": "arn:aws:iam::123456789012:role/SchedulerInvokeRole",
  "Arn": "arn:aws:lambda:us-east-1:123456789012:function:my-function",
  "Input": "{\"key\": \"value\"}",
  "RetryPolicy": {
    "MaximumRetryAttempts": 3,
    "MaximumEventAgeInSeconds": 3600
  },
  "DeadLetterConfig": {
    "Arn": "arn:aws:sqs:us-east-1:123456789012:scheduler-dlq"
  }
}
```

### ECS target specifics

ECS targets require additional configuration (task definition, launch
type, network configuration):

```bash
--target '{
  "RoleArn": "...",
  "Arn": "arn:aws:ecs:us-east-1:123456789012:cluster/my-cluster",
  "EcsParameters": {
    "TaskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/my-task:1",
    "LaunchType": "FARGATE",
    "NetworkConfiguration": {
      "awsvpcConfiguration": {
        "Subnets": ["subnet-aaa111"],
        "SecurityGroups": ["sg-aaa111"],
        "AssignPublicIp": "ENABLED"
      }
    }
  }
}'
```

### Kinesis target specifics

```bash
--target '{
  "RoleArn": "...",
  "Arn": "arn:aws:kinesis:us-east-1:123456789012:stream/my-stream",
  "KinesisParameters": {
    "PartitionKey": "my-partition-key"
  }
}'
```

## IAM role mechanics

### How the Scheduler uses IAM roles

The EventBridge Scheduler assumes a role to invoke the target. This
role is provided in the `RoleArn` field of the target configuration.
The Scheduler does NOT create this role automatically via the CLI —
you must create it (or use an existing one) and grant the Scheduler
permission to assume it.

### Creating the Scheduler invocation role

```bash
# Create the trust policy (allows Scheduler to assume the role)
cat > scheduler-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "scheduler.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
ROLE_ARN=$(aws iam create-role \
  --role-name EventBridgeSchedulerInvokeRole \
  --assume-role-policy-document file://scheduler-trust-policy.json \
  --query 'Role.Arn' --output text \
  --region us-east-1)

# Attach a permissions policy scoped to the target
cat > scheduler-permissions.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:my-function"
    },
    {
      "Effect": "Allow",
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:123456789012:scheduler-dlq"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name EventBridgeSchedulerInvokeRole \
  --policy-name SchedulerInvokePolicy \
  --policy-document file://scheduler-permissions.json \
  --region us-east-1
```

### iam:PassRole requirement

The caller (the entity creating the schedule) must have
`iam:PassRole` permission for the role specified in the target:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::123456789012:role/EventBridgeSchedulerInvokeRole",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "scheduler.amazonaws.com"
        }
      }
    }
  ]
}
```

The `Condition` clause ensures the role can only be passed to the
Scheduler service, not to any other service.

### Least-privilege role pattern

Scope the role to ONLY the specific target ARN:

```json
{
  "Effect": "Allow",
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:us-east-1:123456789012:function:my-specific-function"
}
```

Do NOT use `"Resource": "*"` — this over-privileges the Scheduler role
to invoke any Lambda in the account.

## Schedule groups

### Group lifecycle

```bash
# Create a group
aws scheduler create-schedule-group \
  --name prod-schedules \
  --region us-east-1

# List groups
aws scheduler list-schedule-groups \
  --region us-east-1

# List schedules in a group
aws scheduler list-schedules \
  --group-name prod-schedules \
  --region us-east-1

# Bulk enable all schedules in a group
aws scheduler update-schedule-group \
  --name prod-schedules \
  --state ENABLED \
  --region us-east-1

# Bulk disable all schedules in a group
aws scheduler update-schedule-group \
  --name prod-schedules \
  --state DISABLED \
  --region us-east-1

# Delete a group (must be empty)
aws scheduler delete-schedule-group \
  --name prod-schedules \
  --region us-east-1
```

### Group immutability

- Group assignment is immutable — a schedule CANNOT move between groups
- Group name is immutable — cannot be renamed
- Group CANNOT be deleted if it contains schedules
- To change a schedule's group: delete and recreate with the new group

### Bulk operation patterns

```text
Maintenance window pattern:
  1. Create group: non-critical-schedules
  2. Assign all non-critical schedules to this group
  3. Before deployment: update-schedule-group --state DISABLED
  4. Deploy
  5. After deployment: update-schedule-group --state ENABLED

Environment promotion pattern:
  1. Create groups: staging-schedules, prod-schedules
  2. Staging schedules in staging-schedules
  3. On promotion: disable staging group, enable prod group
  4. Schedules fire in prod with the same configuration

Cost control pattern:
  1. Create group: dev-schedules
  2. Assign all dev environment schedules
  3. Off-hours: update-schedule-group --state DISABLED
  4. On-hours: update-schedule-group --state ENABLED
```

## Retry policy

### Configuration

```bash
--target '{
  "RoleArn": "...",
  "Arn": "...",
  "RetryPolicy": {
    "MaximumRetryAttempts": 3,
    "MaximumEventAgeInSeconds": 3600
  }
}'
```

| Parameter | Range | Default | Description |
|---|---|---|---|
| MaximumRetryAttempts | 0-185 | 185 | Maximum number of retry attempts |
| MaximumEventAgeInSeconds | 60-86400 | 86400 (24h) | Maximum age of an event before it is dropped |

### Retry behavior

- Retries use exponential backoff
- The Scheduler retries on target invocation failures (5xx errors, timeouts)
- The Scheduler does NOT retry on successful invocations that return errors
  (the target must handle application-level errors)
- After MaximumRetryAttempts are exhausted, the event goes to the DLQ

### Setting MaximumRetryAttempts to 0

If `MaximumRetryAttempts` is 0, the Scheduler invokes the target once
with NO retries. Any failure goes directly to the DLQ.

```bash
"RetryPolicy": {
  "MaximumRetryAttempts": 0
}
```

Use this for fire-and-forget schedules where retries are not desired.

## Dead-letter queue (DLQ)

### Configuration

```bash
--target '{
  "RoleArn": "...",
  "Arn": "...",
  "DeadLetterConfig": {
    "Arn": "arn:aws:sqs:us-east-1:123456789012:scheduler-dlq"
  }
}'
```

### DLQ requirements

1. **The SQS queue MUST exist** before schedule creation
2. **The Scheduler role must have `sqs:SendMessage`** on the queue
3. **The queue should have a retention policy** to prevent message loss

```bash
# Create DLQ
aws sqs create-queue \
  --queue-name scheduler-dlq \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=1209600 \
  --region us-east-1

# Get the ARN
DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/scheduler-dlq \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text \
  --region us-east-1)
```

### DLQ message processing

Messages in the DLQ contain the original event payload and error
metadata. Process them with a Lambda consumer or manual inspection:

```python
import json
import boto3

sqs = boto3.client('sqs')

def process_dlq(queue_url):
    response = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
    for message in response.get('Messages', []):
        body = json.loads(message['Body'])
        # body contains: schedule_arn, target_arn, error, event_payload
        print(f"Failed schedule: {body.get('ScheduleArn')}")
        print(f"Error: {body.get('ErrorMessage')}")
        # Reprocess or alert
```

### DLQ queue policy

The DLQ must allow the Scheduler to send messages:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "scheduler.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:123456789012:scheduler-dlq"
    }
  ]
}
```

## CloudWatch metrics

### Available metrics

| Metric | Dimensions | Description |
|---|---|---|
| `Invocations` | ScheduleName | Number of successful target invocations |
| `InvocationsFailed` | ScheduleName | Number of failed invocations |
| `InvocationsFailedToBeSentToDlq` | ScheduleName | Invocations that failed AND failed DLQ delivery |
| `ThrottledEvents` | ScheduleName | Events throttled by the Scheduler |

### Monitoring queries

```bash
# Track invocation success rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Scheduler \
  --metric-name Invocations \
  --start-time 2026-08-04T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --dimensions Name=ScheduleName,Value=hourly-report \
  --region us-east-1

# Track failures
aws cloudwatch get-metric-statistics \
  --namespace AWS/Scheduler \
  --metric-name InvocationsFailed \
  --start-time 2026-08-04T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

### Recommended alarms

```bash
# Alarm: any invocation failure
aws cloudwatch put-metric-alarm \
  --alarm-name scheduler-invocation-failures \
  --namespace AWS/Scheduler \
  --metric-name InvocationsFailed \
  --statistic Sum \
  --period 300 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts \
  --region us-east-1

# Alarm: DLQ delivery failure (critical — events are being lost)
aws cloudwatch put-metric-alarm \
  --alarm-name scheduler-dlq-delivery-failure \
  --namespace AWS/Scheduler \
  --metric-name InvocationsFailedToBeSentToDlq \
  --statistic Sum \
  --period 300 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:critical-alerts \
  --region us-east-1
```

## Terraform examples

```hcl
# IAM role for Scheduler
resource "aws_iam_role" "scheduler" {
  name = "EventBridgeSchedulerInvokeRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

# Permissions scoped to specific targets
resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "SchedulerInvokePolicy"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.report.arn
      },
      {
        Effect   = "Allow"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.scheduler_dlq.arn
      }
    ]
  })
}

# DLQ
resource "aws_sqs_queue" "scheduler_dlq" {
  name                       = "scheduler-dlq"
  message_retention_seconds  = 1209600
  visibility_timeout         = 300
}

# Schedule group
resource "aws_scheduler_schedule_group" "prod" {
  name = "prod-schedules"
}

# Schedule with retry and DLQ
resource "aws_scheduler_schedule" "resilient" {
  name       = "resilient-job"
  group_name = aws_scheduler_schedule_group.prod.name

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(30 minutes)"

  target {
    arn      = aws_lambda_function.report.arn
    role_arn = aws_iam_role.scheduler.arn

    retry_policy {
      maximum_retry_attempts     = 3
      maximum_event_age_in_seconds = 3600
    }

    dead_letter_config {
      arn = aws_sqs_queue.scheduler_dlq.arn
    }
  }
}
```
