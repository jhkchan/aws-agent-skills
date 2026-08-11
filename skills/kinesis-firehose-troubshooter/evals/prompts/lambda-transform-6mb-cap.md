# Eval prompt: lambda-transform-6mb-cap

Diagnose the following Firehose Lambda transform failure. Emit the
standard DIAGNOSIS block.

Diagnosis reference: lambda-transform-6mb-cap
Account: 111111111111
Region: us-east-1
Delivery-stream-name: prod-events-enriched
Destination: s3 (extended, with Lambda transform)
Lambda function: prod-enrichment-fn
Symptom: LambdaFails (transformed batches dropped)

Recent diagnostic output:
- CloudWatch Lambda.Errors: 0 (no exceptions)
- Lambda Duration: 200-400ms (well under the 30s timeout)
- Firehose log: "Response payload exceeds 6 MB" repeatedly;
  full batches routed to S3 error backup.
- Lambda Insights: output record size averages 8 KB after
  enrichment (input ~1 KB; enrichment adds JSON expansion).
- describe-delivery-stream ProcessingConfiguration:
  BufferingHints SizeInMBs=3, IntervalInSeconds=60
- CloudWatch LambdaInvocation.DroppedRecords > 0

Emit the standard DIAGNOSIS block. Identify the root cause via
the 5-layer health check (Step 1, Layer 2).
