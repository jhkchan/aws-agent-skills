# Async APIs and S3 Output — Textract Document Deployer

Deep reference on the asynchronous Textract APIs
(StartDocumentAnalysis, StartDocumentTextDetection,
StartExpenseAnalysis), the S3 OutputConfig pattern, SNS notification
role configuration, and KMS encryption for input and output. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Async API family

### When to use async

The asynchronous APIs are the production default for any multipage
document. They support PDFs and TIFFs up to 3000 pages per job and
write structured results to a customer-owned S3 bucket via
OutputConfig.

| API | Purpose | Page limit | Output |
|---|---|---|---|
| StartDocumentTextDetection | Raw text (lines, words) only | 3000 | OutputConfig + GetDocumentTextDetection |
| StartDocumentAnalysis | Forms, Tables, Queries, Signatures, Layout | 3000 | OutputConfig + GetDocumentAnalysis |
| StartExpenseAnalysis | Invoices, receipts (purpose-built) | 3000 | OutputConfig + GetExpenseAnalysis |

### Anatomy of an async call

```bash
aws textract start-document-analysis \
  --document-location '{"S3Object":{"Bucket":"<input>","Name":"<key>"}}' \
  --feature-types '["FORMS","TABLES","QUERIES"]' \
  --queries-config '{"Queries":[{"Text":"<question>"}]}' \
  --output-config '{"S3Bucket":"<output>","S3Prefix":"<prefix>/"}' \
  --kms-key-id arn:aws:kms:<region>:<acct>:key/<id> \
  --notification-channel '{"SNSTopicArn":"<topic>","RoleArn":"<role>"}' \
  --client-request-token "<idempotency-token>" \
  --job-tag "<human-readable-tag>" \
  --region <region>
```

The call returns a `JobId` immediately. Results are delivered via:
1. SNS push notification (Status SUCCEEDED or FAILED)
2. OutputConfig S3 location (per-page JSON + CSV summaries)
3. Get* API with pagination (MaxResults + NextToken)

### Job status lifecycle

```text
IN_PROGRESS → SUCCEEDED
            → FAILED
            → PARTIAL_SUCCESS (some pages failed)
```

Polling pattern (without SNS):

```bash
JOB_ID="<from-start-call>"
while true; do
  STATUS=$(aws textract get-document-analysis \
    --job-id "$JOB_ID" \
    --max-results 1 \
    --query 'JobStatus' --output text --region us-east-1)
  echo "Status: $STATUS"
  [ "$STATUS" = "SUCCEEDED" ] && break
  [ "$STATUS" = "FAILED" ] && { echo "Job failed"; exit 1; }
  sleep 10
done
```

## OutputConfig — S3 output structure

### Why OutputConfig matters

Without OutputConfig, results are returned only via the Get* API in
paginated chunks. For multipage documents, the JSON can be tens of MB.
OutputConfig writes per-page JSON and structured CSVs to your own S3
bucket, which is cheaper to retrieve and easier to query with Athena.

### Directory layout

```text
s3://<output-bucket>/<prefix>/<job-id>/
  ├── 1/
  │   └── inferred-doc-response-1.json
  ├── 2/
  │   └── inferred-doc-response-2.json
  ├── ...
  ├── key-values/
  │   └── key-values-<job-id>.csv
  ├── queries-results/
  │   └── queries-results-<job-id>.csv
  └── tables/
      └── tables-<job-id>.csv
```

### Region constraint

The OutputConfig bucket MUST be in the same AWS region as the
Textract API call. Cross-region OutputConfig causes
InvalidS3Object or ProvisionedThroughputExceeded.

```bash
# Verify bucket region matches Textract region
aws s3api get-bucket-location --bucket <output-bucket> --region us-east-1
# Expected: LocationConstraint: us-east-1 (or "" for us-east-1)
```

## SNS notification channel

### Notification role

The NotificationChannel parameter requires a RoleArn that Textract
assumes to publish to SNS. This role must:
1. Trust `textract.amazonaws.com` in its trust policy
2. Have `sns:Publish` on the topic ARN in its permission policy

```json
// Trust policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "textract.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```

```json
// Permission policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:123456789012:TextractComplete"
    }
  ]
}
```

### SNS message body

```json
{
  "JobId": "abc12345-...",
  "Status": "SUCCEEDED",
  "API": "StartDocumentAnalysis",
  "Timestamp": 1722816000,
  "DocumentLocation": {
    "S3Object": {
      "Bucket": "doc-input",
      "Name": "invoices/2026-q3.pdf"
    }
  }
}
```

Wire this to a Lambda subscriber or SQS queue for downstream
processing (e.g., fetch the OutputConfig S3 objects and post-process).

## KMS encryption

### Two encryption contexts

- **Input:** if the input document is KMS-encrypted in S3, Textract
  needs `kms:Decrypt` on the encrypting key.
- **Output:** if `--kms-key-id` is specified, Textract uses that key
  to encrypt the OutputConfig JSON. Textract needs
  `kms:GenerateDataKey` and `kms:Decrypt` on that key.

### Key policy grant

```json
{
  "Sid": "AllowTextractToUseKMS",
  "Effect": "Allow",
  "Principal": {"Service": "textract.amazonaws.com"},
  "Action": [
    "kms:Decrypt",
    "kms:GenerateDataKey"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:SourceAccount": "123456789012"
    }
  }
}
```

The `aws:SourceAccount` condition prevents the confused-deputy
problem — without it, any Textract caller in another account could
use your key.

## Document splitting strategy

### Why split

The async APIs hard-fail at 3001+ pages. For oversized documents
(regulatory filings, contracts, mortgage packages), split customer-
side before invoking Textract.

### Splitting pattern

```python
from PyPDF2 import PdfReader, PdfWriter

def split_pdf(input_path, pages_per_chunk=2500):
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    chunks = []
    for start in range(0, total_pages, pages_per_chunk):
        writer = PdfWriter()
        end = min(start + pages_per_chunk, total_pages)
        for page_num in range(start, end):
            writer.add_page(reader.pages[page_num])
        chunk_path = f"{input_path}.part-{start//pages_per_chunk:04d}.pdf"
        with open(chunk_path, "wb") as f:
            writer.write(f)
        chunks.append({
          "path": chunk_path,
          "start_page": start,
          "end_page": end - 1
        })
    return chunks
```

### Aggregation

Submit each chunk as a separate StartDocumentAnalysis job. Track the
chunk index and page offsets in your orchestration (Step Functions or
a queue-based worker) so downstream code can stitch results back
together using the per-page offset.

## Quotas and limits

| Limit | Value | Adjustable |
|---|---|---|
| Max pages per async job | 3000 | No (hard) |
| Max document size (async) | 500 MB | No |
| StartDocumentAnalysis TPS | 1 (default) | Yes (Support Center) |
| GetDocumentAnalysis TPS | 5 (default) | Yes |
| Synchronous AnalyzeDocument max document size | 10 MB | No |
| Synchronous AnalyzeDocument max pages | 1 (single-page) or up to 30 (Tiff/PDF) | No |
| Queries per AnalyzeDocument call | 30 | No |
| Queries per StartDocumentAnalysis job | 500 | No |
