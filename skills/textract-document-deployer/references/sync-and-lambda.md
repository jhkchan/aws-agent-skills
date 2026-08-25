# Sync APIs and Lambda Real-Time — Textract Document Deployer

Deep reference on the synchronous Textract APIs (DetectDocumentText,
AnalyzeDocument, AnalyzeExpense, AnalyzeID), Lambda integration for
real-time single-page extraction, bounding-box geometry, confidence-
score filtering, and Comprehend downstream NLP chaining. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Sync API family

### When to use sync

The synchronous APIs are for single-page (or low-page) documents with
real-time SLAs (< 30s typical). They return the full result in the API
response — no JobId, no polling, no OutputConfig.

| API | Purpose | Input | Output |
|---|---|---|---|
| DetectDocumentText | Raw text + geometry | Bytes (base64) or S3 | Blocks (WORD, LINE) |
| AnalyzeDocument | Forms, Tables, Queries, Signatures, Layout | Bytes or S3 | Blocks (all types) |
| AnalyzeExpense | Invoice/receipt structured fields | Bytes or S3 | ExpenseDocuments |
| AnalyzeID | Identity document fields (DL, passport) | Bytes or S3 | IdentityDocumentFields |

### Sync call examples

**AnalyzeDocument with Forms + Tables:**

```bash
aws textract analyze-document \
  --document '{"S3Object":{"Bucket":"realtime-input","Name":"form.png"}}' \
  --feature-types '["FORMS","TABLES"]' \
  --region us-east-1
```

**AnalyzeDocument with Queries:**

```bash
aws textract analyze-document \
  --document '{"S3Object":{"Bucket":"realtime-input","Name":"form.png"}}' \
  --feature-types '["FORMS","QUERIES"]' \
  --queries-config '{"Queries":[{"Text":"What is the policy number?"}]}' \
  --region us-east-1
```

**AnalyzeExpense:**

```bash
aws textract analyze-expense \
  --document '{"S3Object":{"Bucket":"realtime-input","Name":"receipt.jpg"}}' \
  --region us-east-1
```

**AnalyzeID:**

```bash
aws textract analyze-id \
  --document-pages '[{"S3Object":{"Bucket":"realtime-input","Name":"license.jpg"}}]' \
  --region us-east-1
```

### Page and size limits (sync)

| API | Max document size | Max pages |
|---|---|---|
| DetectDocumentText | 5 MB (PNG/JPEG), 500 MB (PDF/TIFF) | 1 page (PDF/TIFF) |
| AnalyzeDocument | 10 MB | 1 page (PNG/JPEG); up to 30 (PDF/TIFF, region-dependent) |
| AnalyzeExpense | 10 MB | 1 page (PNG/JPEG); up to 15 (PDF/TIFF) |
| AnalyzeID | 5 MB per document page | Up to 2 pages |

## Lambda integration

### Pattern: S3-triggered Lambda

For real-time extraction, deploy a Lambda function triggered by S3
PUT events. The Lambda reads the S3 object, calls the synchronous
AnalyzeDocument, and writes structured results to DynamoDB, S3, or an
API response.

```python
import json
import boto3
import os

s3 = boto3.client("s3")
textract = boto3.client("textract")

CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "75.0"))

def lambda_handler(event, context):
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]

    # Call AnalyzeDocument with Forms + Tables
    response = textract.analyze_document(
        Document={"S3Object": {"Bucket": bucket, "Name": key}},
        FeatureTypes=["FORMS", "TABLES"]
    )

    # Extract key-value pairs above the confidence threshold
    key_map, value_map, block_map = _build_maps(response["Blocks"])
    forms = {}
    for key_block_id, key_text in key_map.items():
        value_block = _find_value(key_block_id, key_map, value_map, block_map)
        if value_block and value_block["Confidence"] >= CONFIDENCE_THRESHOLD:
            forms[key_text] = _text_for(value_block, block_map)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "forms": forms,
            "low_confidence_count": sum(
                1 for b in response["Blocks"]
                if b.get("Confidence", 100) < CONFIDENCE_THRESHOLD
            )
        })
    }

def _build_maps(blocks):
    key_map = {}
    value_map = {}
    block_map = {b["Id"]: b for b in blocks}
    for block in blocks:
        if block["BlockType"] == "KEY_VALUE_SET":
            if "KEY" in block.get("EntityTypes", []):
                key_map[block["Id"]] = _text_for(block, block_map)
            elif "VALUE" in block.get("EntityTypes", []):
                value_map[block["Id"]] = block
    return key_map, value_map, block_map

def _find_value(key_block_id, key_map, value_map, block_map):
    block = block_map[key_block_id]
    for rel in block.get("Relationships", []):
        if rel["Type"] == "VALUE":
            for value_id in rel["Ids"]:
                if value_id in value_map:
                    return value_map[value_id]
    return None

def _text_for(block, block_map):
    parts = []
    for rel in block.get("Relationships", []):
        if rel["Type"] == "CHILD":
            for child_id in rel["Ids"]:
                child = block_map.get(child_id)
                if child and child.get("Text"):
                    parts.append(child["Text"])
    return " ".join(parts)
```

### Lambda IAM policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "textract:AnalyzeDocument",
        "textract:DetectDocumentText",
        "textract:AnalyzeExpense",
        "textract:AnalyzeID"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::realtime-input/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::realtime-output/*"
    }
  ]
}
```

### Lambda sizing

AnalyzeDocument typically takes 1-10 seconds for a single-page
document. Configure Lambda with at least 256 MB memory and a 30-second
timeout. For heavier features (Queries + Forms + Tables), use 512 MB
and a 60-second timeout.

### Failure modes

- **InvalidS3Object:** bucket/key wrong, cross-region S3, missing
  s3:GetObject permission.
- **UnsupportedDocumentException:** corrupt PDF, password-protected
  PDF, or unsupported format.
- **ThrottlingException:** exceed the account's synchronous TPS quota.
  Implement exponential backoff or request a quota increase.
- **Lambda timeout:** document too large for the sync API within
  Lambda's timeout. Switch to async with Step Functions polling.

## Bounding boxes and geometry

### Geometry object

Every Block includes a `Geometry` object with `BoundingBox` and
`Polygon`:

```json
{
  "Geometry": {
    "BoundingBox": {
      "Width": 0.187,
      "Height": 0.038,
      "Left": 0.401,
      "Top": 0.137
    },
    "Polygon": [
      {"X": 0.401, "Y": 0.137},
      {"X": 0.588, "Y": 0.137},
      {"X": 0.588, "Y": 0.175},
      {"X": 0.401, "Y": 0.175}
    ]
  }
}
```

Coordinates are fractions of the page (0.0-1.0). To convert to pixel
coordinates, multiply by page width / height in pixels.

```python
def to_pixels(bbox, page_width, page_height):
    return {
        "left": int(bbox["Left"] * page_width),
        "top": int(bbox["Top"] * page_height),
        "width": int(bbox["Width"] * page_width),
        "height": int(bbox["Height"] * page_height)
    }
```

### Use cases

- **Visual overlays:** draw rectangles on a rendered preview.
- **Region extraction:** crop a sub-region for higher-resolution
  re-processing.
- **Layout validation:** verify a field appears in the expected region
  of the page.

## Confidence scores

### Score range

Every Block (except PAGE) has a `Confidence` field, a float 0-100.

### Thresholding pattern

```python
CONFIDENCE_THRESHOLD = 75.0
review_queue = []
for block in response["Blocks"]:
    if block["BlockType"] == "KEY_VALUE_SET" and block.get("Confidence", 0) < CONFIDENCE_THRESHOLD:
        review_queue.append({
            "block_id": block["Id"],
            "confidence": block["Confidence"],
            "page": block.get("Page", 1)
        })

# Route review_queue to a manual-review SQS queue or DynamoDB table
```

### Choosing a threshold

- **>= 90%:** production-grade (minimal human review).
- **75-90%:** balanced (route borderline cases to manual review).
- **50-75%:** lenient (high human-review overhead).

The right threshold depends on the cost of a wrong extraction vs the
cost of human review. Start at 75% and tune based on precision/recall
on your document set.

## Comprehend integration

### Pipeline shape

```text
Textract (extract text) → Comprehend (entities, PII, sentiment, classify)
```

### Example: entity detection + PII

```python
import boto3

textract = boto3.client("textract")
comprehend = boto3.client("comprehend")

# Step 1: extract text
textract_response = textract.detect_document_text(
    Document={"S3Object": {"Bucket": "docs", "Name": "contract.pdf"}}
)
text = " ".join(
    b["Text"] for b in textract_response["Blocks"]
    if b["BlockType"] in ("LINE", "WORD")
)

# Step 2: detect entities + PII (truncate to Comprehend sync limit)
text_chunk = text[:100_000]
entities = comprehend.detect_entities(Text=text_chunk, LanguageCode="en")
pii = comprehend.detect_pii_entities(Text=text_chunk, LanguageCode="en")

# Step 3: redact PII from the extracted text
redacted = text
for entity in pii["Entities"]:
    redacted = redacted.replace(entity["Text"], "[REDACTED]")
```

### Comprehend limits

- `DetectEntities` synchronous: 100 KB per call
- `DetectPiiEntities` synchronous: 5 KB per call
- For larger documents, use `StartEntitiesDetectionJob` (async, up to
  5 GB per job)

### Comprehend Medical

For clinical documents, use Comprehend Medical (`detect_entities_v2`
or `detect_phi`) instead of generic Comprehend. It returns medical-
specific entity types (DX_NAME, RX_GENERIC, TEST_NAME) and is HIPAA-
eligible.

## Extended from SKILL.md

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
