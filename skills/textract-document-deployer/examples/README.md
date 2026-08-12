# End-to-End Example: Textract Document Deployment

A walkthrough showing how to use the `textract-document-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying an asynchronous Textract pipeline for a multipage
invoice bundle (1450 pages) with Forms + Tables extraction, KMS
encryption, SNS completion notification, and OutputConfig to a
customer-owned S3 bucket. The pipeline needs:

- Input: s3://doc-input/invoices/2026-q3.pdf (1450-page PDF)
- Output: s3://doc-output/textract/ (same region us-east-1)
- Features: FORMS, TABLES
- KMS: arn:aws:kms:us-east-1:123456789012:key/abcd1234-...
- SNS: arn:aws:sns:us-east-1:123456789012:TextractComplete
- IAM: arn:aws:iam::123456789012:role/TextractProcessingRole
- Tags: Project=invoice-automation

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-textract-pipeline
```

Then paste the requirements.

### Option B: Natural language

```
You: "Set up an async Textract pipeline for a 1450-page PDF at
      s3://doc-input/invoices/2026-q3.pdf. Forms + Tables.
      Output to s3://doc-output/textract/. KMS encrypted.
      SNS notify on completion."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy textract document analysis pipeline"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
TEXTRACT_PIPELINE: s3://doc-input/invoices/2026-q3.pdf → FORMS,TABLES → s3://doc-output/textract/
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Input bucket: s3://doc-input/invoices/2026-q3.pdf (region us-east-1)
  [✓] Output bucket: s3://doc-output/textract/ (region us-east-1)
  [✓] API mode: Asynchronous (StartDocumentAnalysis)
  [✓] Feature types: FORMS, TABLES
  [✓] Document format: PDF (1450 pages)
  [✓] Page-count check: PASS (1450 ≤ 3000)
  [✓] IAM — s3:GetObject on input: TextractProcessingRole
  [✓] IAM — s3:PutObject on output: TextractProcessingRole
  [✓] IAM — textract:StartDocumentAnalysis/GetDocumentAnalysis: TextractProcessingRole
  [✓] KMS encryption: arn:aws:kms:us-east-1:123456789012:key/abcd1234-... (input + output)
  [✓] SNS notification: arn:aws:sns:us-east-1:123456789012:TextractComplete (RoleArn TextractNotificationRole)
  [✓] OutputConfig: s3://doc-output/textract/<job-id>/
  [✓] Confidence threshold: 75% (route <75% to manual review)
  [✓] Document splitting: not required
VERIFICATION_COMMANDS:
  aws textract get-document-analysis --job-id <job-id> --region us-east-1
  aws s3 ls s3://doc-output/textract/<job-id>/ --recursive
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Verify input bucket region matches Textract region
aws s3api get-bucket-location --bucket doc-input --region us-east-1

# Step 2: Submit the async StartDocumentAnalysis job
JOB_ID=$(aws textract start-document-analysis \
  --document-location '{"S3Object":{"Bucket":"doc-input","Name":"invoices/2026-q3.pdf"}}' \
  --feature-types '["FORMS","TABLES"]' \
  --output-config '{"S3Bucket":"doc-output","S3Prefix":"textract/"}' \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234-... \
  --notification-channel '{"SNSTopicArn":"arn:aws:sns:us-east-1:123456789012:TextractComplete","RoleArn":"arn:aws:iam::123456789012:role/TextractNotificationRole"}' \
  --job-tag "invoice-automation-2026-q3" \
  --region us-east-1 \
  --query 'JobId' --output text)

echo "JobId: $JOB_ID"

# Step 3: Poll for status (or wait for SNS push)
aws textract get-document-analysis \
  --job-id "$JOB_ID" \
  --max-results 1 \
  --query 'JobStatus' \
  --region us-east-1
# Expected: SUCCEEDED (when complete)

# Step 4: List OutputConfig results in S3
aws s3 ls "s3://doc-output/textract/${JOB_ID}/" --recursive --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Job status and message
aws textract get-document-analysis \
  --job-id "$JOB_ID" \
  --max-results 1 \
  --query '{Status: JobStatus, StatusMessage: StatusMessage}' \
  --region us-east-1

# OutputConfig per-page JSON
aws s3 ls "s3://doc-output/textract/${JOB_ID}/" --recursive --region us-east-1
# Expected: 1/, 2/, ..., 1450/ with inferred-doc-response-*.json
# Plus key-values/, tables/ CSV summaries

# Sample one page's result
aws s3 cp "s3://doc-output/textract/${JOB_ID}/1/inferred-doc-response-1.json" - --region us-east-1 | jq '.Blocks | length'
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| API choice | DetectDocumentText (multipage fails) | StartDocumentAnalysis (async, multipage) | Sync APIs are single-page; multipage needs async |
| Output | Get* pagination only | OutputConfig to customer S3 | Multipage JSON can be tens of MB; OutputConfig writes per-page JSON + CSVs |
| KMS key policy | Forgets Textract grant | kms:Decrypt + kms:GenerateDataKey on textract.amazonaws.com | Confused-deputy protection; without grant, InvalidParameterException |
| SNS notification | No notification role | RoleArn with trust + sns:Publish | NotificationChannel requires RoleArn; otherwise API call fails |
| Page limit | No check | Verify ≤ 3000 pages; split if over | Hard limit; 3001+ pages hard-fails |
| S3 region | Cross-region | Same region as Textract API call | Cross-region causes InvalidS3Object |
| Feature selection | DetectDocumentText for everything | AnalyzeDocument with FeatureTypes | DetectDocumentText returns raw text only; Forms/Tables/Queries need AnalyzeDocument |
| Expense handling | AnalyzeDocument FORMS for invoices | StartExpenseAnalysis (purpose-built) | Invoices/receipts have a dedicated API returning vendor, total, line items |

---

## Related artifacts

- **Skill definition:** `skills/textract-document-deployer/SKILL.md`
- **Async + S3 guide:** `skills/textract-document-deployer/references/async-and-s3.md`
- **Sync + Lambda guide:** `skills/textract-document-deployer/references/sync-and-lambda.md`
- **Slash command:** `commands/aws/deploy-textract-pipeline.md`
- **Eval suite:** `skills/textract-document-deployer/evals/evals.json`
- **Legacy test cases:** `skills/textract-document-deployer/eval/test-cases.yaml`
