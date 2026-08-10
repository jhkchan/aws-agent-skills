# Eval prompt: input-transformer-lambda-deploy

Design an EventBridge rule deployment with input transformation
for the following scenario. Emit the standard PLAN block including
the InputTransformer configuration with InputPathsMap and
InputTemplate.

Design reference: input-transformer-lambda-deploy
Account: 111111111111
Region: us-east-1

Source: AWS S3 object-created events (uploads/ prefix only)
Bucket: my-uploads-bucket
Desired action: invoke Lambda `process-upload` with a SIMPLIFIED
payload containing only bucket, key, and etag (not the full event
envelope).
The Lambda is idempotent on bucket+key+etag.
DLQ: arn:aws:sqs:us-east-1:111111111111:eventbridge-upload-dlq
  (created with 14-day retention).
Lambda ARN: arn:aws:lambda:us-east-1:111111111111:function:process-upload
Lambda invocation permission: granted.

The InputTransformer must extract:
- detail.bucket.name -> <bucket>
- detail.object.key -> <key>
- detail.object.eTag -> <etag>

And produce a JSON payload of the form:
{"bucket":"<bucket>","key":"<key>","etag":"<etag>"}
