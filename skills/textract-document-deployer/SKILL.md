---
name: textract-document-deployer
description: 'Deploys Amazon Textract document-analysis pipelines with production defaults: synchronous APIs (DetectDocumentText, AnalyzeDocument) for single-page real-time extraction, asynchronous APIs (StartDocumentAnalysis, StartDocumentTextDetection, StartExpenseAnalysis) for multipage PDFs up to 3000 pages, S3 document source and output config, SNS notification for async job completion, KMS encryption for input and output, feature selection (Forms, Tables, Queries, Signatures, Expense, Identity), bounding-box geometry and confidence-score handling, Lambda integration for real-time extraction, document splitting for oversized PDFs, service quotas, Comprehend integration for downstream NLP on extracted text. Emits a. Triggers: analyze document, detect document text, extract form fields, extract tables, textract queries, textract expense analysis, textract signature detection, textract identity documents, start document analysis, textract lambda, textract s3 output, textract kms encryption, textract sns notification.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with textract access and an IAM role granting s3:GetObject on the input bucket, s3:PutObject on the output bucket, textract:Start* / Get* / Notify* actions, kms:Decrypt / kms:GenerateDataKey on the KMS key, and sns:Publish if SNS notification is used. Works with Lambda runtimes (boto3 textract client), Step Functions orchestrations, Terraform aws_textract_* data sources, and...'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, textract, document-analysis, ml, deploy, provisioning, forms, tables, queries, expense, lambda, kms, sns
  dependencies: aws-orchestrator
  keywords: aws, textract, document analysis, ocr, forms, tables, queries, signatures, expense, identity documents, ml, deploy, provisioning, synchronous, asynchronous, lambda, kms, sns, s3, comprehend
  when_to_use: Invoke when the user wants to extract text, forms, tables, signatures, expense, or identity data from documents (PDF, TIFF, PNG, JPEG) using Amazon Textract. Covers both synchronous APIs for single-page real-time extraction (DetectDocumentText, AnalyzeDocument) and asynchronous APIs for multipage batch extraction (StartDocumentAnalysis, StartExpenseAnalysis, StartDocumentTextDetection) with S3 input/output, SNS completion notification, KMS encryption, Lambda integration, and Comprehend downstream NLP. Do NOT invoke for Amazon Transcribe (audio), Amazon Rekognition (image/video ML), or pure OCR via Textract DetectDocumentText without downstream analysis.
---

# Textract Document Deployer

An AWS CloudOps agent skill that deploys Amazon Textract document-
analysis pipelines with correct defaults. The skill walks the operator
through feature selection (Forms, Tables, Queries, Signatures, Expense,
Identity), synchronous vs asynchronous API choice, S3 input/output
configuration, KMS encryption, SNS completion notifications, Lambda
integration for real-time extraction, document splitting for oversized
PDFs, service quotas, and Comprehend downstream NLP, captures the
document-processing topology, explains why each default matters, and
emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

analyze document, detect document text, extract form fields, extract
tables, textract queries, textract expense analysis, textract signature
detection, textract identity documents, start document analysis, textract
lambda, textract s3 output, textract kms encryption, textract sns
notification.

## STRICT output contract

When this skill is invoked with a Textract-deployment request
(extract text/forms/tables/expense/identity from documents, set up async
multipage extraction, configure SNS/KMS/Lambda integration, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY checklist
defined in the "Output format" section using the literal all-caps labels
`TEXTRACT_PIPELINE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Feature selection (Forms, Tables, Queries, ...) | Core feature matrix |
| Step 2 — Synchronous vs asynchronous API choice | API selection |
| Step 3 — S3 document source and output config | Storage |
| Step 4 — KMS encryption | Encryption |
| Step 5 — SNS notification for async completion | Async notification |
| Step 6 — Lambda integration for real-time extraction | Real-time path |
| Step 7 — Bounding boxes and confidence scores | Geometry |
| Step 8 — Document splitting for large PDFs | Quota handling |
| Step 9 — Comprehend integration for downstream NLP | NLP chaining |
| Step 10 — Identity documents and signatures | Specialized features |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/async-and-s3.md | Async API + S3 output detail |
| references/sync-and-lambda.md | Sync API + Lambda real-time detail |

## Mindset

**One-line takeaway:** Textract synchronous APIs
(DetectDocumentText, AnalyzeDocument) work on a single page (or up to
the per-call page limit) for real-time use; asynchronous APIs
(StartDocumentAnalysis, StartExpenseAnalysis,
StartDocumentTextDetection) work on multipage PDFs up to 3000 pages
with S3 input, SNS notification, and an output config that writes
structured JSON to your own S3 bucket. Feature selection at
`AnalyzeDocument` time — Forms, Tables, Queries, Signatures — is what
turns raw OCR into structured business data.

Three misconceptions dominate Textract misdesign at provisioning time:

- **"DetectDocumentText is sufficient for forms/tables."** It is not.
  `DetectDocumentText` returns only raw text lines and words (with
  geometry and confidence). To get form key-value pairs, table cells,
  signatures, or natural-language query answers, you MUST use
  `AnalyzeDocument` with the appropriate `FeatureTypes` (FORMS, TABLES,
  QUERIES, SIGNATURES). A baseline model often reaches for
  `DetectDocumentText` when the operator needs structured form data.

- **"The synchronous API handles multipage PDFs."** It does NOT.
  `AnalyzeDocument` and `DetectDocumentText` accept a single document
  (page). For multipage PDFs (up to 3000 pages), you MUST use the
  asynchronous `StartDocumentAnalysis` / `StartDocumentTextDetection` /
  `StartExpenseAnalysis` APIs with an S3 document source. Using the
  sync API on a multipage PDF returns an error or processes only the
  first page.

- **"Textract output is just the API response."** For async jobs, the
  output is configurable. The `OutputConfig` parameter writes the
  structured JSON to a customer-owned S3 bucket, and the
  `S3ObjectPrefix` keeps results organized per job. Without
  `OutputConfig`, results are returned only in the `Get*` API response
  (which can be tens of MB for multipage documents).

## Configuration dependency graph (novel heuristic)

Textract configurations are NOT independent. The feature types selected
determine the API choice; the API choice determines sync vs async; the
async path requires S3 input and (recommended) S3 output, SNS, and KMS.
Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| IAM role (or direct IAM) | s3:GetObject on input bucket | Textract returns InvalidParameterException if S3 access is missing | Textract to read documents |
| Synchronous AnalyzeDocument | Inline bytes (base64) OR S3 location; feature types specified | Limited to single-page or low-page documents; multipage PDFs rejected | real-time extraction in Lambda |
| Asynchronous StartDocumentAnalysis | S3 location for input; S3 bucket in same region | without OutputConfig, results only available via Get* (paginated, large) | multipage processing up to 3000 pages |
| OutputConfig (S3 output) | S3 bucket in same region as Textract job; s3:PutObject grant | bucket region MUST match Textract region | structured JSON results in your bucket |
| KMS encryption | KMS key policy grants Textract service kms:GenerateDataKey + kms:Decrypt | KMS key must be in same region | encrypts input (if encrypted in S3) and output JSON |
| SNS notification | SNS topic in same region; Textract service allowed sns:Publish | without SNS, must poll GetDocumentAnalysis | push notification on job completion |
| Lambda integration | Lambda in same region; IAM includes textract:Start* / Get* | Lambda synchronous API for single-page only | real-time extraction endpoint |
| Comprehend NLP | Textract output (text or forms) extracted and passed to Comprehend | Comprehend has its own quotas and regions | entity detection, PII, classification on extracted text |
| Document splitting | Customer-side logic (Textract does NOT split) | Textract enforces 3000-page hard limit per async job | oversized PDF processing |
| Queries feature | AnalyzeDocument with FeatureTypes=[QUERIES] + QueriesConfig | Queries requires the QUERIES feature type AND a QueriesConfig block | natural-language questions on forms |
| Expense analysis | StartExpenseAnalysis (async) or AnalyzeExpense (sync) | Expense uses a SEPARATE API family; Forms/Tables feature types do not apply | invoices/receipts structured line items |
| Identity documents | AnalyzeID (sync, dedicated API) | Identity uses a SEPARATE API; Lending uses a SEPARATE async API | driver's license, passport fields |

**The sync-vs-async choice row is the one a baseline model misses.**
A naive deployment calls `DetectDocumentText` for everything. The
correct heuristic recognizes that multipage PDFs and most production
workloads need the async API with S3 input, OutputConfig, and SNS. The
procedure below forces an explicit API choice.

**Cross-dependency gotchas:**
- S3 input bucket and OutputConfig bucket MUST be in the same AWS
  region as the Textract API call. Cross-region S3 fails silently or
  with a confusing InvalidS3Object exception.
- KMS-encrypted input documents require the Textract service role (or
  caller) to have kms:Decrypt on the encrypting key; the output JSON
  uses a separate KMS key grant (kms:GenerateDataKey).
- SNS topic MUST be in the same region as the Textract job. The role
  needs sns:Publish on the topic ARN, and Textract's service principal
  must be allowed.
- The Queries feature is selected via `FeatureTypes=[QUERIES]` AND
  requires a `QueriesConfig` block with one or more `Text` queries. A
  missing QueriesConfig returns no query results.
- Expense analysis and identity documents use SEPARATE API families
  (`AnalyzeExpense` / `StartExpenseAnalysis` and `AnalyzeID`). They are
  NOT invoked through `AnalyzeDocument`.

## Expert heuristic: choosing sync vs async

A baseline model says "use Textract." The correct heuristic recognizes
that Textract has two distinct operational shapes.

```text
Document profile:
  ├── Single page (PNG/JPEG/TIFF/PDF), real-time, < 30s SLA
  │     → Synchronous API
  │       DetectDocumentText  (raw text + geometry)
  │       AnalyzeDocument     (text + Forms / Tables / Queries / Signatures)
  │       AnalyzeExpense      (invoices/receipts, single doc)
  │       AnalyzeID           (driver's license / passport)
  │
  ├── Multipage PDF (2-3000 pages), batch, minutes
  │     → Asynchronous API with S3 input + OutputConfig + SNS + KMS
  │       StartDocumentTextDetection  (raw text, multipage)
  │       StartDocumentAnalysis       (Forms / Tables / Queries / Signatures, multipage)
  │       StartExpenseAnalysis        (invoices/receipts, multipage batch)
  │
  └── Over 3000 pages
        → Customer-side document splitting into <3000-page chunks
          then StartDocumentAnalysis per chunk; aggregate downstream
```

**Key implication:** the async API is the production default for any
multipage document. Lambda real-time extraction is only for single-page
or low-page documents where the 15-minute (or configured) Lambda timeout
is not exceeded.

## Expert heuristic: feature-type selection

Feature types are selected at `AnalyzeDocument` time. Each adds
structured output on top of raw OCR.

```text
Use case                                → FeatureTypes         → API
─────────────────────────────────────────────────────────────────────────
Raw text extraction (lines, words)     → (none — use Detect)  → DetectDocumentText
Form key-value pairs (labels+values)   → [FORMS]              → AnalyzeDocument
Tabular data (rows, columns, headers)  → [TABLES]             → AnalyzeDocument
Natural-language questions on forms    → [QUERIES]            → AnalyzeDocument
Signature locations on page            → [SIGNATURES]         → AnalyzeDocument
Forms + Tables together                → [FORMS, TABLES]      → AnalyzeDocument
Forms + Tables + Queries               → [FORMS, TABLES, QUERIES]
Invoice / receipt line items           → (separate API)       → AnalyzeExpense / StartExpenseAnalysis
Driver's license / passport            → (separate API)       → AnalyzeID
```

**The Queries feature lets you ask natural-language questions of
forms.** Example: "What is the policy number?" returns the value and
its bounding box, even if the form layout varies. This is more
flexible than FORMS key-value extraction, which depends on matching
labels.

## Expert heuristic: async API supports up to 3000 pages per job

The async APIs (`StartDocumentAnalysis`, `StartDocumentTextDetection`,
`StartExpenseAnalysis`) support multipage PDFs up to 3000 pages per
job (hard limit). The sync APIs support a single page (or a small
number of pages depending on the API and document type). For oversized
PDFs, split the document customer-side before invoking Textract.

```text
PDF page count:
  ├── 1 page            → sync OK (Lambda real-time)
  ├── 2-3000 pages      → async (StartDocumentAnalysis)
  └── >3000 pages       → split into chunks of ≤3000 pages, async per chunk
```

**Key implication:** the 3000-page limit is a hard quota. Plan for
document splitting in any document-management pipeline that handles
large reports, contracts, or regulatory filings.

## Expert heuristic: expense analysis is purpose-built for invoices and receipts

`AnalyzeExpense` (sync) and `StartExpenseAnalysis` (async) use a
purpose-built ML model for invoices and receipts. They return
structured fields (vendor, invoice number, total, line items) without
requiring Forms/Tables feature configuration.

```text
Invoice / receipt processing decision:
  ├── Need structured fields (vendor, total, line items)
  │     → AnalyzeExpense / StartExpenseAnalysis (purpose-built)
  │       Returns: ExpenseDocuments[] with SummaryFields[] and LineItems[]
  │
  └── Need custom form layout extraction
        → AnalyzeDocument with FORMS, TABLES, QUERIES
```

**Key implication:** do NOT use AnalyzeDocument with FORMS for invoices
if you need vendor name, total, or line-item extraction. Use
AnalyzeExpense — it returns these as structured fields with confidence
scores.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 input bucket exists (same region) | Textract must read documents from S3 in the same region | `aws s3api head-bucket --bucket <input-bucket>` |
| S3 output bucket exists (same region) | OutputConfig writes JSON to a customer-owned bucket | `aws s3api head-bucket --bucket <output-bucket>` |
| IAM grant: s3:GetObject on input | Textract service (or caller) must read documents | Review role policy |
| IAM grant: s3:PutObject on output | Textract writes structured JSON to output bucket | Review role policy |
| IAM grant: textract:Start*/Get*/Notify* | Required to invoke async APIs and retrieve results | Review IAM policy |
| KMS key (if encryption enabled) | KMS-encrypted inputs require kms:Decrypt; outputs use kms:GenerateDataKey | `aws kms describe-key --key-id <key-id>` |
| KMS key policy grants Textract | Textract service principal needs kms:GenerateDataKey + kms:Decrypt | Review key policy |
| SNS topic (if async + notification) | SNS topic in same region; Textract needs sns:Publish | `aws sns get-topic-attributes --topic-arn <arn>` |
| Document format supported | PDF, TIFF, PNG, JPEG | Confirm file type |
| Document under 3000 pages (async) | Hard limit per async job | Verify page count, plan splitting |
| Feature type selected | Determines structured output | Choose from FORMS/TABLES/QUERIES/SIGNATURES |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Feature selection (Forms, Tables, Queries, Signatures, Expense, Identity)

`AnalyzeDocument` accepts a `FeatureTypes` list. Multiple features can
be combined (e.g., `[FORMS, TABLES, QUERIES]`).

| Feature | What it adds | API |
|---|---|---|
| FORMS | Key-value pairs (field labels + values) with confidence | AnalyzeDocument |
| TABLES | Tabular structure (rows, columns, headers, merged cells) | AnalyzeDocument |
| QUERIES | Natural-language question answering on forms (with QueriesConfig) | AnalyzeDocument |
| SIGNATURES | Signature locations (bounding boxes) on the page | AnalyzeDocument |
| LAYOUT | Reading order and structural layout elements | AnalyzeDocument |
| (Expense) | Invoice/receipt structured fields — separate API | AnalyzeExpense / StartExpenseAnalysis |
| (Identity) | Driver's license / passport fields — separate API | AnalyzeID |

**Choose feature types based on document type and downstream use:**
- Invoices/receipts → Expense API (not AnalyzeDocument FORMS).
- Custom forms → FORMS, optionally + QUERIES.
- Spreadsheets → TABLES.
- Contracts with signatures → FORMS + SIGNATURES.
- Variable-layout forms → QUERIES (more flexible than FORMS).

## Step 2 — Synchronous vs asynchronous API choice

| Decision factor | Synchronous | Asynchronous |
|---|---|---|
| Document length | Single page (or low page count per API limits) | Up to 3000 pages |
| Latency requirement | Real-time (< 30s typical) | Minutes (batch) |
| Input source | Inline bytes (base64) OR S3 Object | S3 Object (required) |
| Output | API response only | OutputConfig (S3) recommended |
| Notification | None (caller waits) | SNS topic (optional) |
| Encryption | KMS via API parameters | KMS via API parameters |
| APIs | DetectDocumentText, AnalyzeDocument, AnalyzeExpense, AnalyzeID | StartDocumentTextDetection, StartDocumentAnalysis, StartExpenseAnalysis |
| Result retrieval | Direct in response | GetDocumentAnalysis / GetExpenseAnalysis (paginated) OR OutputConfig S3 |
| Lambda integration | Yes (single-page real-time) | Yes but with Step Functions for polling |

**Rule of thumb:** if the document is more than 1-2 pages or the
extraction takes more than a few seconds, use async.

## Step 3 — S3 document source and output config

The async APIs require an S3 location for input. The OutputConfig
parameter writes structured JSON results to a customer-owned S3 bucket.

```bash
aws textract start-document-analysis \
  --document-location '{"S3Object":{"Bucket":"my-input-bucket","Name":"invoices/2026/q3/batch-001.pdf"}}' \
  --feature-types '["FORMS","TABLES"]' \
  --output-config '{"S3Bucket":"my-output-bucket","S3Prefix":"textract-output/"}' \
  --notification-channel '{"SNSTopicArn":"arn:aws:sns:us-east-1:123456789012:TextractComplete","RoleArn":"arn:aws:iam::123456789012:role/TextractNotificationRole"}' \
  --region us-east-1
```

OutputConfig writes per-page JSON plus structured CSV summaries
(`key-values/`, `queries-results/`, `tables/`) to your bucket. Full
OutputConfig directory layout is in `references/async-and-s3.md`. The
OutputConfig bucket MUST be in the same region as the Textract job —
cross-region S3 causes `InvalidS3Object` or similar errors.

## Step 4 — KMS encryption

Textract supports KMS encryption for both input documents (if stored
encrypted in S3) and output JSON. Specify the KMS key ID via
`--kms-key-id`.

```bash
aws textract start-document-analysis \
  --document-location '{"S3Object":{"Bucket":"my-input-bucket","Name":"encrypted/batch-001.pdf"}}' \
  --feature-types '["FORMS","TABLES","QUERIES"]' \
  --queries-config '{"Queries":[{"Text":"What is the invoice total?"}]}' \
  --output-config '{"S3Bucket":"my-output-bucket","S3Prefix":"textract-encrypted/"}' \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234-... \
  --region us-east-1
```

**KMS key policy requirements:** the Textract service principal
(`textract.amazonaws.com`) must have `kms:GenerateDataKey` and
`kms:Decrypt` on the key. The calling role must have `kms:Decrypt` for
reading encrypted input. Full key policy JSON with the
`aws:SourceAccount` confused-deputy condition is in
`references/async-and-s3.md`.

## Step 5 — SNS notification for async completion

The NotificationChannel parameter configures an SNS topic that
Textract publishes to when the async job completes (success or
failure).

```bash
aws textract start-document-analysis \
  --document-location '{"S3Object":{"Bucket":"my-input","Name":"batch.pdf"}}' \
  --feature-types '["FORMS","TABLES"]' \
  --notification-channel '{"SNSTopicArn":"arn:aws:sns:us-east-1:123456789012:TextractComplete","RoleArn":"arn:aws:iam::123456789012:role/TextractNotificationRole"}' \
  --region us-east-1
```

**Notification role:** the RoleArn must trust `textract.amazonaws.com`
and have `sns:Publish` on the topic. Full trust + permission policy
JSON is in `references/async-and-s3.md`.

The SNS message body includes `JobId`, `Status` (SUCCEEDED / FAILED),
and `API` (e.g., StartDocumentAnalysis). Wire this to a Lambda or SQS
queue for downstream processing.

## Step 6 — Lambda integration for real-time extraction

For single-page or low-page documents with real-time SLAs, deploy
Textract behind a Lambda function using the synchronous
`AnalyzeDocument` API. Full Python handler and IAM policy are in
`references/sync-and-lambda.md`; the core call is:

```python
import boto3
textract = boto3.client("textract")

def lambda_handler(event, context):
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    response = textract.analyze_document(
        Document={"S3Object": {"Bucket": bucket, "Name": key}},
        FeatureTypes=["FORMS", "TABLES"]
    )
    return {"statusCode": 200, "body": response["Blocks"]}
```

**Lambda IAM policy (minimum):** `textract:AnalyzeDocument` on `*`
and `s3:GetObject` on the input bucket. See the reference for the
full JSON.

**Critical:** Lambda's synchronous AnalyzeDocument has the same
per-call page limits as the direct API. For multipage, route through
Step Functions with the async StartDocumentAnalysis API instead.

## Step 7 — Bounding boxes and confidence scores

Every Textract Block (WORD, LINE, KEY_VALUE_SET, TABLE, CELL, SIGNATURE,
QUERY) includes:

- **Geometry:** `BoundingBox` (Top, Left, Width, Height as fractions of
  page dimensions) and `Polygon` (list of points). Use these to draw
  overlays or extract regions.
- **Confidence:** float 0-100. Use a threshold (typically 50-90%) to
  filter low-confidence extractions in downstream validation.

```python
# Filter low-confidence form values
CONFIDENCE_THRESHOLD = 75.0
for block in response["Blocks"]:
    if block["BlockType"] == "KEY_VALUE_SET":
        confidence = block["Confidence"]
        if confidence < CONFIDENCE_THRESHOLD:
            print(f"Low confidence: {confidence:.1f}% — review manually")
```

**Key implication:** confidence scores are the primary signal for
human-in-the-loop review workflows. Set a threshold that matches your
accuracy SLA; route low-confidence extractions to a manual review
queue.

## Step 8 — Document splitting for large PDFs

Textract does NOT split oversized documents. For PDFs over 3000 pages,
split the document customer-side (e.g., with `PyPDF2` or `qpdf`) before
invoking Textract. Submit each chunk as a separate
StartDocumentAnalysis job and aggregate downstream using chunk index
and page offsets. Full splitting code is in
`references/async-and-s3.md`.

```python
# Pattern: split into ≤3000-page chunks, submit one job per chunk
chunks = split_pdf("s3://doc-input/large.pdf", pages_per_chunk=2500)
for i, chunk in enumerate(chunks):
    submit_textract_job(chunk, tag=f"large-part-{i:04d}")
```

**Key implication:** the 3000-page limit is a hard quota. Plan for
document splitting in any document-management pipeline that handles
large reports, contracts, or regulatory filings.

## Step 9 — Comprehend integration for downstream NLP

Textract output (raw text or form values) can be passed to Amazon
Comprehend for entity detection, key phrase extraction, sentiment
analysis, PII detection, or custom classification. Full pipeline code
is in `references/sync-and-lambda.md`; the pattern is:

```python
textract = boto3.client("textract")
comprehend = boto3.client("comprehend")

# Extract text, then run NLP on the result
doc = textract.detect_document_text(Document={"S3Object": {...}})
text = " ".join(b["Text"] for b in doc["Blocks"] if b["BlockType"] in ("LINE", "WORD"))
entities = comprehend.detect_entities(Text=text[:100_000], LanguageCode="en")
pii = comprehend.detect_pii_entities(Text=text[:5_000], LanguageCode="en")
```

**Critical:** Comprehend has its own quotas — 100 KB per synchronous
`DetectEntities` call, 5 KB per `DetectPiiEntities` call. For larger
documents, use async `StartEntitiesDetectionJob` or chunk the Textract
output.

## Step 10 — Identity documents and signatures

Identity documents (driver's license, passport) use the dedicated
`AnalyzeID` API (synchronous). It returns structured fields like
document number, expiration, first/last name, address, date of birth.

```bash
aws textract analyze-id \
  --document-pages '[{"S3Object":{"Bucket":"my-bucket","Name":"id/drivers-license.jpg"}}]' \
  --region us-east-1
```

Signatures are detected via `AnalyzeDocument` with
`FeatureTypes=["SIGNATURES"]`. Each signature is returned as a
SIGNATURE Block with a bounding box.

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **Queries feature GA (2023-2024):** Natural-language question
  answering on forms. More flexible than FORMS key-value extraction
  for variable-layout documents. Available in both sync
  (AnalyzeDocument) and async (StartDocumentAnalysis) APIs.

- **Signatures feature GA (2023-2024):** Bounding-box detection of
  signatures on documents. Available via AnalyzeDocument with
  FeatureTypes=["SIGNATURES"].

- **Expense Analysis improvements (2023-2024):** Enhanced vendor name
  and line-item extraction accuracy. OutputConfig now supports
  structured CSV outputs for queries and tables.

- **Lending Analysis (2023-2024):** Specialized async API
  (StartLendingAnalysis) for mortgage and lending documents
  (pay stubs, W-2s, 1099s, bank statements).

- **Layout feature (2023-2024):** AnalyzeDocument with
  FeatureTypes=["LAYOUT"] returns reading-order structural elements
  (titles, headers, footers, sections).

- **OutputConfig enhancements (2024-2025):** Per-page JSON output and
  structured CSV files (key-values, queries-results, tables) written
  directly to S3, reducing Get* pagination overhead.

- **European region expansion (2024-2025):** Textract available in
  additional EU regions (eu-west-3, eu-south-1, eu-north-1).

- **General Availability in APAC (2024-2025):** Textract GA in
  ap-southeast-3 (Jakarta) and ap-east-1 (Hong Kong), expanding
  options for APAC data-residency requirements.

## NEVER do these things

1. **NEVER use DetectDocumentText when you need forms, tables, queries,
   signatures, or expense data.** DetectDocumentText returns only raw
   text. Use AnalyzeDocument with the appropriate FeatureTypes, or
   AnalyzeExpense / AnalyzeID for specialized document types.

2. **NEVER call the synchronous API on a multipage PDF expecting all
   pages.** The sync APIs are designed for single-page (or low-page)
   documents. Use StartDocumentAnalysis / StartDocumentTextDetection
   for multipage PDFs up to 3000 pages.

3. **NEVER submit a PDF over 3000 pages without splitting.** The async
   API hard-fails at 3001+ pages. Split customer-side into chunks of
   ≤3000 pages and submit each as a separate job.

4. **NEVER use cross-region S3 buckets for input or OutputConfig.**
   Both the input bucket and the OutputConfig bucket MUST be in the
   same region as the Textract API call. Cross-region S3 causes
   InvalidS3Object or ProvisionedThroughputExceeded errors.

5. **NEVER forget the notification role for SNS.** The
   NotificationChannel requires a RoleArn that trusts
   textract.amazonaws.com and has sns:Publish on the topic. Without
   it, the API call fails.

6. **NEVER use AnalyzeDocument FORMS for invoices and receipts.**
   Invoices and receipts have a dedicated API (AnalyzeExpense /
   StartExpenseAnalysis) that returns structured vendor, total, and
   line-item fields. AnalyzeDocument FORMS does not.

7. **NEVER assume Textract output is small.** Multipage documents can
   produce tens of MB of structured JSON. Use OutputConfig to write
   results to S3 rather than fetching them all via Get* pagination.

8. **NEVER skip the KMS key policy for Textract.** If the input
   document is KMS-encrypted, Textract needs kms:Decrypt. If output
   encryption is configured, Textract needs kms:GenerateDataKey. Both
   must be granted to the Textract service principal.

9. **NEVER assume confidence scores are binary (good/bad).** Set a
   threshold appropriate to your use case (typically 50-90%). Route
   low-confidence extractions to a human review queue.

10. **NEVER confuse AnalyzeID with AnalyzeDocument.** Identity
    documents (driver's license, passport) use the dedicated AnalyzeID
    API. AnalyzeDocument does not return identity-document structured
    fields.

## Output format

```text
TEXTRACT_PIPELINE: <input-s3-uri> → <feature-types> → <output-s3-uri>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Input bucket: s3://<bucket>/<key> (region <region>)
  [✓|✗] Output bucket: s3://<bucket>/<prefix> (region <region>)
  [✓|✗] API mode: Synchronous (AnalyzeDocument) | Asynchronous (StartDocumentAnalysis)
  [✓|✗] Feature types: FORMS | TABLES | QUERIES | SIGNATURES | EXPENSE | IDENTITY
  [✓|✗] Document format: <PDF|TIFF|PNG|JPEG> (<page-count> pages)
  [✓|✗] Page-count check: PASS (<n> ≤ 3000) | FAIL (<n> > 3000 — split required)
  [✓|✗] IAM — s3:GetObject on input: <role>
  [✓|✗] IAM — s3:PutObject on output: <role>
  [✓|✗] IAM — textract:Start*/Get*: <role>
  [✓|✗] KMS encryption: <key-id> (input + output) | Disabled
  [✓|✗] SNS notification: <topic-arn> (RoleArn <role>) | Disabled
  [✓|✗] Lambda integration: <function-name> (sync real-time) | Not used
  [✓|✗] OutputConfig: s3://<bucket>/<prefix>/<job-id>/
  [✓|✗] Queries config: <n> queries (if QUERIES feature) | Not used
  [✓|✗] Confidence threshold: <threshold>% (downstream review filter)
  [✓|✗] Document splitting: not required | <n> chunks of ≤3000 pages
  [✓|✗] Comprehend integration: <detect-entities|detect-pii|classify> | Not used
VERIFICATION_COMMANDS:
  aws textract get-document-analysis --job-id <job-id> --region <region>
  aws textract describe-document-text-detection --job-id <job-id> --region <region>  (if StartDocumentTextDetection)
  aws s3 ls s3://<output-bucket>/<prefix>/<job-id>/ --recursive
```

### Worked example — async multipage Forms+Tables with SNS, KMS, OutputConfig

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
  [✓] IAM — s3:GetObject on input: arn:aws:iam::123456789012:role/TextractProcessingRole
  [✓] IAM — s3:PutObject on output: arn:aws:iam::123456789012:role/TextractProcessingRole
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

## Domain

AWS CloudOps / Amazon Textract Document Analysis & OCR Pipeline
Provisioning.

## AWS documentation

- **Textract Developer Guide** — https://docs.aws.amazon.com/textract/latest/dg/
- **AnalyzeDocument API** — https://docs.aws.amazon.com/textract/latest/dg/API_AnalyzeDocument.html
- **StartDocumentAnalysis API** — https://docs.aws.amazon.com/textract/latest/dg/API_StartDocumentAnalysis.html
- **DetectDocumentText API** — https://docs.aws.amazon.com/textract/latest/dg/API_DetectDocumentText.html
- **OutputConfig** — https://docs.aws.amazon.com/textract/latest/dg/API_OutputConfig.html
- **NotificationChannel** — https://docs.aws.amazon.com/textract/latest/dg/API_NotificationChannel.html
- **Queries feature** — https://docs.aws.amazon.com/textract/latest/dg/queryresponse.html
- **Expense Analysis** — https://docs.aws.amazon.com/textract/latest/dg/invoices-receipts.html
- **Identity Documents (AnalyzeID)** — https://docs.aws.amazon.com/textract/latest/dg/identitydocument.html
- **Textract quotas** — https://docs.aws.amazon.com/textract/latest/dg/limits-document.html
- **KMS encryption** — https://docs.aws.amazon.com/textract/latest/dg/security_iam_encrypt-with-kms.html
