# End-to-end usage scenario: eventbridge-pipe-deployer

A walkthrough showing the skill producing a deployment plan for a
production EventBridge Pipe from DynamoDB Streams to Lambda with a
filter pattern, batch windowing, and pipe-level DLQ. Demonstrates the
READY_TO_DEPLOY verdict, architecture checklist, and ordered
deploy-command list.

## Input (user prompt)

> Provision an EventBridge Pipe for our Orders table. We have a
> DynamoDB Streams stream on the table and want to send only CONFIRMED
> orders to our orders-processor Lambda in batches of ~100 records
> (5-second window). Failed batches should land in our existing
> `prod-pipe-dlq` SQS queue. The Lambda already has a resource policy
> allowing invoke from pipes.amazonaws.com.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — source stream
   region matches pipe region, stream status ENABLED, target Lambda
   state Active with the required resource policy, DLQ policy grants
   the pipe role, IAM trust policy scoped with SourceAccount and
   SourceArn conditions.
2. **Source semantics:** Identifies DynamoDB Streams source. Pipe
   owns the polling; no Lambda event-source mapping needed.
3. **Filter:** Validates the filter pattern as JSON matching
   `dynamodb.NewImage.status.S = CONFIRMED`.
4. **Batch behavior:** 5s window, 100 records, 3 retries, 1-hour
   record age. AUTOMATIC_BISECT recommended on partial failures.
5. **DLQ topology:** DynamoDB Streams source — DLQ lives on the
   pipe (`DeadLetterConfig.Arn`). Pipe role needs `sqs:SendMessage`.
6. **Verdict:** READY_TO_DEPLOY — all checklist dimensions pass.

## Expected output

```text
PIPE: prod-orders-pipe
VERDICT: READY_TO_DEPLOY
TARGET: prod-orders-pipe
PRE_CHECKS:
  - [PASS] DynamoDB Streams arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01 resolves StreamStatus=ENABLED
  - [PASS] Source region us-east-1 matches pipe region
  - [PASS] Filter pattern {"dynamodb":{"NewImage":{"status":{"S":"CONFIRMED"}}}} valid JSON
  - [PASS] Target Lambda arn:aws:lambda:us-east-1:111111111111:function:orders-processor resolves state=Active
  - [PASS] Target resource policy grants lambda:InvokeFunction to pipes.amazonaws.com
  - [PASS] Batch window 5s in range 0-300
  - [PASS] Batch size 100 within DynamoDB Streams cap (1000)
  - [PASS] DLQ arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq policy grants sqs:SendMessage to pipe role
  - [PASS] Pipe role trust policy scoped to pipes.amazonaws.com with SourceAccount=111111111111
  - [PASS] IAM principal holds pipes:CreatePipe, StartPipe, DescribePipe
STEPS:
  1. CONFIRM: About to create-pipe prod-orders-pipe in account 111111111111. Reads DynamoDB Streams Orders, filter CONFIRMED, Lambda target orders-processor, 5s batch window, DLQ prod-pipe-dlq. Estimated cost: $0.50/mo base + $0.50/million invocations. Proceed? (yes/no)
  2. aws pipes create-pipe --name prod-orders-pipe --role-arn arn:aws:iam::111111111111:role/EventBridgePipes-prod-orders --source "arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01T00:00:00.000" --source-parameters '{"DynamoDBStreamParameters":{"StartingPosition":"LATEST","BatchSize":100,"MaximumBatchingWindowInSeconds":5,"MaximumRecordAgeInSeconds":3600,"MaximumRetryAttempts":3,"OnPartialBatchItemFailure":"AUTOMATIC_BISECT","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq"}}}' --filter-criteria '{"Filters":[{"Pattern":"{\"dynamodb\":{\"NewImage\":{\"status\":{\"S\":\"CONFIRMED\"}}}}"}]}' --target "arn:aws:lambda:us-east-1:111111111111:function:orders-processor" --target-parameters '{"LambdaParameters":{"InvocationType":"REQUEST_RESPONSE"}}'
  3. aws pipes start-pipe --name prod-orders-pipe
POST_VERIFY:
  - (pending execution)
  - describe-pipe returns CurrentState=RUNNING
  - Insert an Order with status=CONFIRMED; orders-processor invoked within 10s
  - Insert an Order with status=PENDING; no target invocation (filter drops it)
  - Inject poison record; verify DLQ prod-pipe-dlq receives it after 3 retries
SOURCE: DynamoDB Streams arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01 region us-east-1
FILTER: {"dynamodb":{"NewImage":{"status":{"S":"CONFIRMED"}}}}
ENRICHMENT: none
TARGET: Lambda arn:aws:lambda:us-east-1:111111111111:function:orders-processor
BATCH: window 5s size 100 retry 3 age 3600s
DLQ: arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq (pipe-level)
NOTES:
  - Filter selectivity: only CONFIRMED orders reach Lambda. PENDING / CANCELLED records filtered out pre-target.
  - OnPartialBatchItemFailure=AUTOMATIC_BISECT isolates poison records within 3-4 retries.
  - Cost: $0.50/mo base + $0.50/million invocations. Lambda compute priced separately.
```

## What the baseline (no-skill) response misses

A generic assistant without this skill would:
- Suggest adding a Lambda event-source mapping on the stream
  (would double-deliver records — Pipe is the poller, not Lambda).
- Not enumerate the 10 pre-check dimensions (source state, region
  match, target resource policy, DLQ topology, IAM trust scope).
- Not distinguish pipe-level vs. source-queue DLQ (the silent
  failure mode for SQS sources).
- Not include the CONFIRM gate with cost estimate.
- Not produce a deterministic VERDICT block for downstream
  automation.

The skill converts an open-ended "set up a DynamoDB Streams pipe"
prompt into a deterministic, pre-checked, ordered deploy plan with
a single READY_TO_DEPLOY or PREREQUISITES_MISSING verdict.
