# Sources, Targets, and Pipe Behavior Reference

Supplementary reference for the EventBridge Pipe Deployer skill. Use
when planning source parameters, target resource policies, batch
behavior, or DLQ topology across the six supported source types.

## Source matrix

| Source | Pull model | Required parameters | DLQ location | Notes |
|---|---|---|---|---|
| DynamoDB Streams | Pipe polls shards | `StartingPosition`, `BatchSize`, `MaximumBatchingWindowInSeconds`, `MaximumRecordAgeInSeconds`, `OnPartialBatchItemFailure`, `DeadLetterConfig` | Pipe-level (`DeadLetterConfig.Arn`) | Stream must be `ENABLED`. Table must have `StreamSpecification` enabled. |
| Kinesis | Pipe polls shards | `StartingPosition`, `BatchSize`, `MaximumBatchingWindowInSeconds`, `MaximumRecordAgeInSeconds`, `OnPartialBatchItemFailure`, `DeadLetterConfig` | Pipe-level | Stream must be `ACTIVE`. |
| SQS | Pipe calls `ReceiveMessage` | `BatchSize` | Source queue's `RedrivePolicy` | Pipe-level `DeadLetterConfig` is ignored. Configure the source queue's redrive policy. |
| MSK | Pipe joins Kafka consumer group | `TopicName`, `ConsumerGroupID`, `StartingPosition`, `BatchSize`, `AuthType`, `MaximumRecordAgeInSeconds`, `DeadLetterConfig` | Pipe-level | Cluster `ACTIVE`. AuthType: `SASL_SCRAM_512_AUTH`, `SASL_SCRAM_256_AUTH`, `IAM`, `MTLS`. |
| Amazon MQ | Pipe consumes from broker | `QueueName`, `BatchSize`, `MaximumBatchingWindowInSeconds`, `Credentials` (Secrets Manager secret ARN) | Pipe-level | Broker state `RUNNING`. ActiveMQ classic, ActiveMQ Artemis, RabbitMQ all supported. |
| Self-managed Kafka | Pipe joins consumer group | `TopicName`, `ConsumerGroupID`, `StartingPosition`, `BatchSize`, `AuthType`, `ServerRootCA` (optional), `VpcSubnets/SecurityGroups` (for VPC-restricted brokers), `MaximumRecordAgeInSeconds`, `DeadLetterConfig` | Pipe-level | VPC config required for private clusters. |

## Target matrix

| Target | Required target parameters | Pipe role permission | Resource policy |
|---|---|---|---|
| Lambda | `InvocationType` REQUEST_RESPONSE | `lambda:InvokeFunction` | Optional — supports resource-based policy from `pipes.amazonaws.com`. |
| Step Functions | `StateMachineArn`; for Express sync enrichment use `StartSyncExecution` | `states:StartExecution` (Standard) / `states:StartSyncExecution` (Express sync enrichment) | State machine policy must allow pipe role. |
| EventBridge bus | `EventBusName` | `events:PutEvents` | Bus resource policy optional. |
| SQS | `MessageGroupId` (FIFO queues), `MessageDeduplicationId` | `sqs:SendMessage` | Queue policy must allow pipe role. |
| SNS | `MessageGroupId` (FIFO topics) | `sns:Publish` | Topic policy must allow pipe role. |
| ECS task | `TaskDefinitionArn`, `ClusterArn`, `TaskCount`, `Overrides`, `EnableECSManagedTags`, `EnableExecuteCommand`, `LaunchType`, `NetworkConfiguration`, `PropagateTags`, `ReferenceId`, `Tags` | `ecs:RunTask`, `iam:PassRole` on task execution + task roles | Task role grants the container's AWS access. |
| API Gateway | `Stage`, `Method`, `Path`, `HttpMethod` (REST API), `Headers`, `QueryStringParameters`, `RequestBody` | `apigateway:POST` | Resource policy optional for REST APIs. |
| API Destination | `ApiDestinationArn`, `Headers`, `QueryStringParameters`, `HttpMethod`, `RequestBody` | `events:InvokeApiDestination` | Connection resource holds the auth config. |
| Redshift (Provisioned) | `ClusterName`, `Database`, `DbUser`, `SqlStatements`, `Sqls`, `SecretManagerArn` (optional), `StatementName`, `WithEvent` | `redshift-data:ExecuteStatement`, `redshift:GetClusterCredentials` (if using IAM auth), `secretsmanager:GetSecretValue` (if using secret) | Cluster parameter group controls user access. |
| Redshift Serverless | `WorkgroupName`, `Database`, `Sqls`, `WithEvent` | `redshift-serverless:GetCredentials`, `redshift-data:ExecuteStatement` | Workgroup manages credentials. |
| SageMaker Pipeline | `SageMakerPipelineParameters` (PipelineParameterList) | `sagemaker:StartPipelineExecution` | Pipeline resource policy optional. |
| AWS Batch | `JobDefinitionArn`, `JobName`, `JobQueueArn`, `ArraySize`, `Parameters`, `RetryStrategy`, `ContainerOverrides` | `batch:SubmitJob`, `iam:PassRole` on job role | Job queue + job definition must exist. |

## Batch behavior deep dive

### DynamoDB Streams / Kinesis

```
Stream -> [Pipe polls shard iterator] -> [Batch assembly]
  Window: MaximumBatchingWindowInSeconds (0-300s)
  Size cap: MaximumBatchSize (1-1000 DDB / 1-10000 Kinesis)
  Age cap: MaximumRecordAgeInSeconds (60-86400s)
  -> [Filter (optional)]
  -> [Enrichment (optional)]
  -> [Target invocation]
  Retry: MaximumRetryAttempts (0-185) with exponential backoff
  Failure: OnPartialBatchItemFailure = AUTOMATIC_BISECT halves the batch
  Exceeded: record goes to DeadLetterConfig.Arn
```

### SQS (different model)

```
Queue -> [Pipe ReceiveMessage] -> [Batch up to BatchSize (1-10000)]
  -> [Filter (optional)]
  -> [Enrichment (optional)]
  -> [Target invocation]
  Retry: MaximumRetryAttempts (0-185) — pipe retries the whole batch
  Failure: VisibilityTimeout expires -> message returns to source queue
  Exceeded: source queue's RedrivePolicy moves message to source queue's DLQ
```

The pipe-level `DeadLetterConfig` is **ignored** for SQS sources.
Configure the source queue's `RedrivePolicy` with `maxReceiveCount`
(3-5 typical) and a DLQ ARN.

## Filter pattern rules

Filter patterns match the **source's raw record schema** before
enrichment:

| Source | Pattern matches |
|---|---|
| DynamoDB Streams | `dynamodb.NewImage`, `OldImage`, `Keys`, `StreamViewType`, `eventName` (INSERT/MODIFY/REMOVE) |
| Kinesis | Decoded record data (JSON object) |
| SQS | `body` (JSON if parseable) |
| MSK / Amazon MQ / self-managed Kafka | Decoded record value (JSON if parseable) |

Maximum pattern length: 4096 chars. Validate the pattern shape against
a sample source record before deploying — malformed patterns silently
filter everything.

## MSK / self-managed Kafka consumer groups

| Consumer group layout | Behavior |
|---|---|
| One pipe, unique group | Pipe receives all records from assigned partitions. |
| Two pipes, same group | Partitions split between the pipes. Throughput halved per pipe. Use for scaling past one pipe's capacity. |
| Two pipes, different groups | Both pipes receive all records (fan-out). Use for parallel consumers with different logic. |

`StartingPosition` applies only on first start of the consumer group:
- `LATEST` — only records arriving after pipe start
- `TRIM_HORIZON` — from the earliest available offset
- `AT_TIMESTAMP` — from a specific timestamp

## Amazon MQ credentials

The `Credentials` parameter references an AWS Secrets Manager secret
containing:

```json
{
  "username": "<broker-username>",
  "password": "<broker-password>"
}
```

The pipe role needs `secretsmanager:GetSecretValue` on the secret ARN.
The broker must be in `RUNNING` state — `CREATION_FAILED`,
`REBOOTING`, `CRITICAL_ACTION_REQUIRED` block pipe start.

## IAM role trust policy (canonical)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pipes.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "<account-id>"},
      "ArnEquals": {"aws:SourceArn": "arn:aws:pipes:<region>:<account-id>:pipe/<pipe-name>"}
    }
  }]
}
```

The `SourceAccount` and `SourceArn` conditions prevent the confused-
deputy problem — without them, any principal that can assume the role
can use it to read from the source. Always emit both conditions in the
PRE_CHECKS row.
