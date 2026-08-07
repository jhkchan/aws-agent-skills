# Eval prompt: dlq-idempotency-gap

Review the following EventBridge workflow and emit the standard
ARCHITECTURE block (BUS, PATTERN, TARGETS, RETRY, SAFETY, AUDIT,
VERDICT, GAP, TEMPLATE). Identify gaps and recommend fixes.

Design reference: dlq-idempotency-gap
Account: 111111111111
Region: us-east-1

Existing rule on default bus:
  Name: s3-object-created-trigger
  Pattern: source=aws.s3, detail-type=Object Created
  Target: Lambda process-upload (ARN: arn:aws:lambda:us-east-1:111111111111:function:process-upload)
  RetryPolicy: defaults (185 attempts / 24h)
  DeadLetterConfig: NONE

Consumer state: the Lambda does not dedupe on
bucket+key+etag. CloudWatch shows duplicate invocations for
the same S3 object.
