---
description: Deploy an Amazon Textract document-analysis pipeline with production-grade defaults (sync vs async API selection, Forms/Tables/Queries/Signatures/Expense/Identity feature selection, S3 input + OutputConfig, KMS encryption, SNS notification, Lambda integration for real-time extraction, Comprehend downstream NLP, document splitting for oversized PDFs). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "analyze document"
  - "detect document text"
  - "extract form fields"
  - "extract tables from document"
  - "textract queries"
  - "textract expense analysis"
  - "textract signature detection"
  - "textract identity documents"
  - "start document analysis"
  - "textract lambda"
  - "textract s3 output"
  - "textract kms encryption"
  - "textract sns notification"
  - "textract pipeline"
  - "deploy textract"
  - "document analysis pipeline"
  - "ocr pipeline"
  - "invoice extraction"
  - "receipt extraction"
routes_to: textract-document-deployer
---

# /aws:deploy-textract-pipeline

Activate the `textract-document-deployer` skill and deploy an Amazon
Textract document-analysis pipeline with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Feature selection (Forms, Tables, Queries, Signatures, Expense,
   Identity)
2. Synchronous vs asynchronous API choice (single-page vs multipage)
3. S3 document source and OutputConfig (customer-owned S3 output)
4. KMS encryption for input and output
5. SNS notification for async completion
6. Lambda integration for real-time single-page extraction
7. Bounding boxes and confidence-score filtering
8. Document splitting for PDFs over 3000 pages
9. Comprehend integration for downstream NLP
10. Identity documents (AnalyzeID) and Signatures
11. Recent features (Queries, Layout, Lending, region expansion)

## When to use

- You need to extract text, forms, tables, or signatures from documents.
- You are processing invoices or receipts (Expense Analysis).
- You need natural-language question answering on forms (Queries).
- You are building a real-time extraction endpoint behind Lambda.
- You are running a multipage batch extraction job.
- You need identity-document field extraction (driver's license, passport).
- You need KMS encryption and SNS notification for an async pipeline.
- You need Comprehend integration for NLP on extracted text.

## When NOT to use

- **Amazon Transcribe** — audio transcription uses a different service.
- **Amazon Rekognition** — image/video ML uses a different service.
- **Amazon Bedrock document parsing** — different model-based pipeline.
- **Pure S3 / Glue ETL** — not document OCR.
- **Auditing existing Textract jobs** — use Textract audit skills.

## How to invoke

### Slash command

```
/aws:deploy-textract-pipeline
```

Then provide: input S3 bucket + key, output S3 bucket + prefix,
feature types (FORMS / TABLES / QUERIES / SIGNATURES / EXPENSE /
IDENTITY), API mode (sync vs async), KMS key ID (if encryption),
SNS topic ARN (if notification), Lambda function name (if real-time),
confidence threshold, tags.

### Natural language

Any of these routes to the same skill:

- "set up an async Textract pipeline for a multipage PDF"
- "extract forms and tables from documents in S3"
- "use Textract Queries to ask questions of a form"
- "deploy Lambda to call Textract AnalyzeDocument on uploads"
- "process invoices with Textract Expense Analysis"

### CLI routing

```bash
node cli/bin/cli.js route "deploy textract document analysis pipeline"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to deploy Textract
document-analysis workloads. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-textract-pipeline

     Set up an async Textract pipeline for a 1450-page PDF at
     s3://doc-input/invoices/2026-q3.pdf. Forms + Tables.
     Output to s3://doc-output/textract/. KMS encrypted.
     SNS notify on completion.

Skill:
  TEXTRACT_PIPELINE: s3://doc-input/invoices/2026-q3.pdf → FORMS,TABLES → s3://doc-output/textract/
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] API mode: Asynchronous (StartDocumentAnalysis)
    [✓] Feature types: FORMS, TABLES
    [✓] Page-count check: PASS (1450 ≤ 3000)
    [✓] KMS encryption: arn:aws:kms:us-east-1:...:key/abcd1234-...
    [✓] SNS notification: arn:aws:sns:us-east-1:...:TextractComplete
    [✓] OutputConfig: s3://doc-output/textract/<job-id>/
  VERIFICATION_COMMANDS:
    aws textract get-document-analysis --job-id <job-id> --region us-east-1
    aws s3 ls s3://doc-output/textract/<job-id>/ --recursive
```

## References

- Skill definition: `skills/textract-document-deployer/SKILL.md`
- Async + S3 guide: `skills/textract-document-deployer/references/async-and-s3.md`
- Sync + Lambda guide: `skills/textract-document-deployer/references/sync-and-lambda.md`
- Eval suite: `skills/textract-document-deployer/evals/evals.json`
