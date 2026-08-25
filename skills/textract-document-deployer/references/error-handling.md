# Error Handling — Textract Document Deployer

API failure deep dives moved verbatim from SKILL.md. Loaded on demand.

## Error handling

### InvalidS3Object exception
- The S3 object is missing, in the wrong region, or the IAM role lacks
  s3:GetObject. Verify the bucket and object key, confirm the region
  matches the Textract API region, and review the IAM policy.

### AccessDeniedException on KMS
- The Textract service principal (or caller role) lacks kms:Decrypt
  (for encrypted input) or kms:GenerateDataKey (for encrypted output).
  Update the KMS key policy to grant the required actions.

### Job status IN_PROGRESS or FAILED
- For IN_PROGRESS, poll GetDocumentAnalysis with nextToken until Status
  is SUCCEEDED or FAILED. For FAILED, check the SNS message for the
  error reason (common: oversized PDF, unsupported format, KMS
  access).

### ProvisionedThroughputExceeded
- The Textract transaction rate exceeds the account quota. Request a
  quota increase via the AWS Support Center, or throttle the client.

### Lambda timeout on synchronous AnalyzeDocument
- The document is too large for the Lambda timeout, or too many pages
  for the sync API. Reduce the document size, increase the Lambda
  timeout and memory (proportionally), or switch to the async API
  with Step Functions for polling.

### Queries results empty
- The QUERIES FeatureType was specified without a QueriesConfig block,
  or the queries are not answerable from the document. Verify
  QueriesConfig is present and the queries reference fields visible on
  the page.
