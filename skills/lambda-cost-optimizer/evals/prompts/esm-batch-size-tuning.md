# Eval prompt: esm-batch-size-tuning

Optimise the following Lambda function for cost. Walk the invocation-
frequency analysis (event source mapping batch size tuning) and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

FunctionName: fn-esm-batch-size-tuning
Runtime: nodejs20.x
MemorySize: 512 MB
Architecture: x86_64
Region: us-east-1
Pricing: on-demand

Metrics (last 30 days):
  - Duration avg: 120 ms, p95: 180 ms (for batch of 10)
  - Invocations: 730,000,000/month
  - Errors: 1,500 (0.0002%)
  - Memory utilization: avg 210 MB (41% of 512 MB)

Event Source Mapping:
  - EventSourceArn: arn:aws:sqs:us-east-1:<acct>:high-volume-queue
  - BatchSize: 10 (default)
  - MaximumBatchingWindowInSeconds: 0 (default)
  - FunctionResponseTypes: ["ReportBatchItemFailures"]

Queue metrics:
  - Messages sent: ~1,000,000/hour (730M/month)
  - Average message size: 4 KB

Workload context: SQS message normalizer. Each invocation processes a
batch of 10 messages, does a DB upsert per message. DB upsert is
amortized — batch of 50 takes ~350 ms (not 600 ms). FunctionResponseTypes
is set for partial batch failure reporting.
