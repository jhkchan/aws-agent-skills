# Eval prompt: subscription-filter-lambda-concurrency-exhausted

Diagnose the CloudWatch Logs not-ingesting scenario for the following
subscription-filter fan-out. Walk the symptom-driven diagnostic tree
and emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).

Symptom: the Lambda destination
`fn-subscription-filter-lambda-concurrency-exhausted` that processes
log events from three source log groups is missing approximately 30%
of expected events under load. CloudWatch shows the source log groups
receiving events, but the Lambda's `Invocations` metric is lower than
`IncomingLogEvents` across the three source groups.

```text
Destination Lambda: fn-subscription-filter-lambda-concurrency-exhausted
Account concurrent-invocations quota: 1000
Subscription delivery cap (2x quota): 2000

aws logs describe-subscription-filters (per source log group):
  3 source log groups each have one subscription filter pointing to
  arn:aws:lambda:us-east-1:111111111111:function:fn-subscription-filter-lambda-concurrency-exhausted

aws cloudwatch get-metric-statistics (AWS/Lambda,
  ConcurrentExecutions for the destination, last hour):
  Maximum: 1000 (sustained for 20 minutes)
  Throttles: 124

aws lambda get-account-settings:
  AccountLimit.ConcurrentExecutions: 1000

aws cloudwatch get-metric-statistics (AWS/Logs,
  IncomingLogEvents across the three source groups, last hour):
  Sum per minute: ~2500/minute
  Lambda Invocations for the destination: ~1750/minute
  (700 events/minute are being dropped)

Destination Lambda reserved concurrency: NOT SET
```

Subscription filters deliver to Lambda at up to 2x the account's
concurrent-invocations quota (a per-account subscription budget). A
fan-out across several high-volume log groups can exhaust this budget
and silently drop batches. Provisioning reserved concurrency for the
destination, reducing fan-out, or switching to Kinesis as the
destination are the standard fixes.
