# IAM, DLQ, and Batch Window Reference

Supplementary reference for the EventBridge Pipe Deployer skill. Use
when designing the pipe IAM role, DLQ topology, or batch window tuning
across the six supported source types.

## Pipe role permission templates

### DynamoDB Streams source

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodbstreams:DescribeStream",
        "dynamodbstreams:GetShardIterator",
        "dynamodbstreams:GetRecords",
        "dynamodb:DescribeTable",
        "dynamodb:DescribeContinuousBackups"
      ],
      "Resource": [
        "arn:aws:dynamodb:<region>:<acct>:table/<table>/stream/*",
        "arn:aws:dynamodb:<region>:<acct>:table/<table>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:<region>:<acct>:<dlq-name>"
    }
  ]
}
```

### Kinesis source

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:DescribeStream",
        "kinesis:DescribeStreamSummary",
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "kinesis:ListShards",
        "kinesis:SubscribeToShard"
      ],
      "Resource": "arn:aws:kinesis:<region>:<acct>:stream/<name>"
    }
  ]
}
```

### SQS source

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:<region>:<acct>:<source-queue>"
    }
  ]
}
```

Note: for SQS source, the DLQ policy is on the source queue (via
`RedrivePolicy`), not the pipe role. The source queue's
`RedrivePolicy` lets SQS itself move messages; no pipe role grant
needed for the DLQ.

### MSK source

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
        "kafka-cluster:DescribeCluster"
      ],
      "Resource": "arn:aws:kafka:<region>:<acct>:cluster/<name>/<uuid>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:ReadData",
        "kafka-cluster:DescribeTopic"
      ],
      "Resource": "arn:aws:kafka:<region>:<acct>:topic/<cluster>/<uuid>/<topic>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:DescribeGroup",
        "kafka-cluster:AlterGroup"
      ],
      "Resource": "arn:aws:kafka:<region>:<acct>:group/<cluster>/<uuid>/<consumer-group>"
    }
  ]
}
```

For `AuthType=IAM`, the pipe role IS the Kafka client identity. For
`SASL_SCRAM_*`, the pipe role needs `secretsmanager:GetSecretValue`
on the SCRAM secret associated with the cluster.

### Amazon MQ source

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:<region>:<acct>:secret:<broker-creds-secret>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "mq:DescribeBroker",
        "mq:DescribeUser"
      ],
      "Resource": "arn:aws:mq:<region>:<acct>:broker:<broker-id>"
    }
  ]
}
```

### Self-managed Kafka source

Same shape as MSK plus optional VPC permissions if the broker is in
a VPC (most common):

```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:CreateNetworkInterface",
    "ec2:DescribeNetworkInterfaces",
    "ec2:DeleteNetworkInterface",
    "ec2:DescribeSubnets",
    "ec2:DescribeSecurityGroups"
  ],
  "Resource": "*"
}
```

## Enrichment + target permission add-ons

| Stage | Permission | Resource |
|---|---|---|
| Lambda enrichment/target | `lambda:InvokeFunction` | enrichment ARN + target ARN |
| Step Functions enrichment | `states:StartSyncExecution` (Express sync) | state machine ARN |
| Step Functions target | `states:StartExecution` | state machine ARN |
| EventBridge bus target | `events:PutEvents` | bus ARN |
| SQS target | `sqs:SendMessage` | target queue ARN |
| SNS target | `sns:Publish` | target topic ARN |
| ECS task target | `ecs:RunTask`, `iam:PassRole` on task execution + task roles | cluster + task definition ARNs |
| API Gateway target | `apigateway:POST` | REST API stage ARN |
| API Destination target | `events:InvokeApiDestination` | API Destination ARN |
| Redshift target | `redshift-data:ExecuteStatement`, `redshift:GetClusterCredentials` or `redshift-serverless:GetCredentials`, `secretsmanager:GetSecretValue` (if using secret) | cluster/workgroup + secret ARN |
| SageMaker target | `sagemaker:StartPipelineExecution` | pipeline ARN |
| AWS Batch target | `batch:SubmitJob`, `iam:PassRole` on job role | job queue + job definition ARNs |

## DLQ topology cheat sheet

| Source | Where DLQ lives | How records arrive |
|---|---|---|
| DynamoDB Streams | Pipe-level (`DeadLetterConfig.Arn`) | Records exceeding `MaximumRetryAttempts` OR `MaximumRecordAgeInSeconds` are forwarded by the pipe. |
| Kinesis | Pipe-level | Same as DDB Streams. |
| MSK | Pipe-level | Same. |
| Amazon MQ | Pipe-level | Same. |
| Self-managed Kafka | Pipe-level | Same. |
| SQS | Source queue's `RedrivePolicy` | Source queue's own `maxReceiveCount` moves messages to the queue's DLQ after `ReceiveCount` exceeds the threshold. Pipe-level `DeadLetterConfig` ignored. |

Always emit the DLQ topology as a PRE_CHECKS row clarifying which
model applies.

## Batch window tuning

| Workload | Recommended window | Reason |
|---|---|---|
| Real-time UI updates (latency-critical) | 0-1s | Minimize end-to-end latency. |
| Order processing | 5-10s | Balance latency vs. batch efficiency. |
| Analytics aggregation | 60-300s | Coalesce records into larger batches for cost efficiency. |
| Stream-triggered Step Functions | 30-60s | One orchestration per batch reduces state machine starts. |
| Stream-triggered AWS Batch | 60-300s | Coalesce records into one Batch job submission. |
| SQS source (any workload) | Window ignored — set to 0 and tune `BatchSize` only | SQS `VisibilityTimeout` controls consumption. |

## Confused-deputy prevention

The pipe role trust policy MUST include both:

- `aws:SourceAccount` equals the pipe's owning account
- `aws:SourceArn` equals `arn:aws:pipes:<region>:<acct>:pipe/<name>`

Without these, any AWS principal that can assume the role can use it
to consume from the source. AWS Config rule `eventbridge-pipe-role-trust-check`
(2024) flags non-scoped trust policies as non-compliant.

## Cost model

- Per-pipe base: $0.50/month (2026 pricing, us-east-1).
- Per-million-invocations: $0.50.
- Per-GB-data-processed: variable by source (DynamoDB Streams streams
  priced as DDB read capacity; Kinesis priced as Kinesis RPU; SQS
  priced as SQS API calls; MSK/MQ priced by broker).
- Enrichment Lambda / Step Functions cost: standard compute pricing.

A pipe processing 100M records/month with a Lambda enrichment costs
roughly: $0.50 pipe + $50 invocations + Lambda compute.
