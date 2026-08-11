# Eval: object-lambda-pii-redaction

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Object Lambda AP + transform function + reserved concurrency

## Prompt

Build an Object Lambda access point "pii-redacted-olap" over
bucket "raw-customer-data" (account 123456789012, region
us-east-1). Supporting standard AP name: "raw-customer-ap"
(Internet origin). Transform Lambda function ARN:
"arn:aws:lambda:us-east-1:123456789012:function:pii-redact-fn".
Transform action: GetObject. Reserve 30 concurrent executions
on the Lambda.
