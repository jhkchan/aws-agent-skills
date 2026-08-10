# Eval prompt: cw-emf-missing-aws-field

Diagnose the following CloudWatch custom metric emission failure.
Walk the CUSTOM_METRIC_NOT_ARRIVING decision tree and emit the
standard VERDICT block.

## Scenario

A Lambda function `worker-fn` emits an Embedded Metric Format (EMF)
blob per invocation to log group `/aws/lambda/worker-fn`. The
operator expects a metric `JobsProcessed` under namespace
`MyApp/Worker` but `list-metrics` returns nothing under that
namespace.

## Known facts

- `aws cloudwatch list-metrics --namespace MyApp/Worker` returns an
  empty list (no metrics published under this namespace).
- AWS CloudTrail shows NO `PutMetricData` API calls for the
  `worker-fn` role in the last hour (Lambda uses EMF, not
  `PutMetricData` directly).
- `aws logs filter-log-events --log-group-name /aws/lambda/worker-fn
  --start-time <epoch-ms> --limit 5` returns recent log entries
  shaped like:
  ```json
  {
    "timestamp": 1691616000000,
    "JobsProcessed": 42,
    "ServiceName": "worker"
  }
  ```
  The blob has NO `_aws` field. There is no `CloudWatchMetrics`
  array. The Lambda uses Powertools for AWS Lambda (TypeScript)
  Metrics utility, but on inspection the developer confirms they
  did not call `metrics.flush()` or use the `logMetrics` decorator,
  so the EMF directive was never attached to the log entry.
- The Lambda execution role has a policy allowing
  `logs:CreateLogStream` and `logs:PutLogEvents` on
  `arn:aws:logs:us-east-1:111111111111:log-group:/aws/lambda/worker-fn:*`
  (logs are arriving correctly).

## Symptom

`JobsProcessed` is never visible in CloudWatch metrics. The log
entries arrive correctly in CloudWatch Logs.
