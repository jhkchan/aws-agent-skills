# Training Data and Classifier Modes — Comprehend Classifier Deployer

Deep reference on training data formats (CSV line-level, Augmented
Manifest from Ground Truth), multi-class vs multi-label data
preparation, classifier input modes (PLAIN_TEXT vs Native PDF),
training data volume requirements, and class balance considerations.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## CSV format detail

### Multi-class CSV

```csv
label,text
billing,"I need a refund for my last invoice"
technical,"The API returns a 500 error"
general,"How do I reset my password?"
billing,"Invoice 4521 has the wrong amount"
technical,"Cannot connect to the database"
```

- Column 1: label (the class — one per row).
- Column 2: the document text, quoted if it contains commas.
- One row per document.
- The header row is required: `label,text`.

### Multi-label CSV

```csv
label,text
politics|economy,"The new tax bill will impact GDP growth by 2%"
sports|world,"Olympic opening ceremony draws record global audience"
technology|health|"AI-powered diagnostic tool approved by the FDA"
```

- Column 1: pipe-separated labels (`label1|label2|label3`).
- A document can have one or more labels.
- The same document text can appear in multiple rows with different
  single labels (alternative format).

### CSV pitfalls

- **No header row:** training fails with an opaque error. Always
  include `label,text` as the first line.
- **Unquoted text with commas:** the CSV parser splits on the comma,
  producing extra columns. Quote all text fields.
- **UTF-8 BOM:** some text editors add a byte-order mark. Remove it
  before uploading.
- **Empty lines:** the parser may fail on trailing empty lines. Strip
  them.

```bash
# Validate CSV before uploading
head -5 training.csv
wc -l training.csv
# Check for malformed rows (not exactly 2 comma-separated fields)
awk -F',' 'NF!=2 {print NR": "$0}' training.csv
```

## Augmented Manifest format detail

### From SageMaker Ground Truth

Ground Truth produces augmented manifest files automatically when
labeling jobs complete. The format is JSONL (one JSON object per line).

```json
{"source":"The invoice amount is incorrect","target":"billing","metadata":{"source-ref":"s3://bucket/raw/doc1.txt"}}
{"source":"The server is down","target":"technical","metadata":{"source-ref":"s3://bucket/raw/doc2.txt"}}
```

- `source`: the document text (for PLAIN_TEXT mode).
- `target`: the label assigned by the Ground Truth labeling workforce.
- `metadata`: optional additional fields from the labeling job.

### For Native PDF mode

```json
{"source":"s3://my-bucket/pdfs/invoice_001.pdf","target":"invoice"}
{"source":"s3://my-bucket/pdfs/contract_002.pdf","target":"contract"}
```

- `source`: S3 URI to the PDF file (NOT inline text).
- `target`: the label.
- The S3 bucket must be in the same region as the Comprehend job.
- PDFs must be under 500 MB and 2000 pages.

### Multi-label Augmented Manifest

```json
{"source":"The new tax bill impacts GDP","target":["politics","economy"]}
{"source":"AI diagnostic tool approved by FDA","target":["technology","health"]}
```

- `target` is a JSON array of labels.

### Augmented Manifest with train/test split

```bash
aws comprehend create-document-classifier \
  --data-format AUGMENTED_MANIFEST \
  --augmented-manifests '[{
    "AttributeNames": ["source","target"],
    "S3Uri": "s3://my-bucket/training/manifest.jsonl",
    "Split": 0.2
  }]' \
  ...
```

- `Split`: fraction of data to use as test data (0.2 = 20% test, 80%
  training). Comprehend automatically splits the augmented manifest.

## Native PDF mode detail

### When to use Native PDF

- Documents are multi-page PDFs (contracts, invoices, reports).
- Layout information (tables, headers, columns) is relevant to
  classification.
- Documents contain scanned images (Native PDF mode uses Textract OCR).

### When NOT to use Native PDF

- Documents are short text (emails, tickets, reviews). Use PLAIN_TEXT.
- Documents are already extracted text. Use PLAIN_TEXT with CSV.
- You need faster training (Native PDF is slower due to document
  processing).

### PDF requirements

- Format: PDF (not Word, not images directly — convert to PDF first).
- Max file size: 500 MB.
- Max pages: 2000 pages per document.
- Must be stored in S3 in the same region as the Comprehend job.
- Scanned PDFs are supported via Textract OCR integration.

### Common Native PDF pitfall

Using PLAIN_TEXT mode with extracted text instead of Native PDF loses
layout features. In tests, Native PDF mode can improve classification
accuracy by 10-15% on document-type classification tasks where layout
matters (invoices vs contracts vs letters).

## Training data volume and class balance

### Minimum documents per class

| Volume per class | Expected quality | Recommendation |
|---|---|---|
| < 50 | Very poor | BLOCK — collect more data |
| 50-200 | Moderate | Prototype only |
| 200-1000 | Good | Production-ready |
| 1000-5000 | Very good | Production-grade |
| 5000+ | Excellent | Diminishing returns |

### Class balance verification

```bash
# For CSV: count documents per class
awk -F',' 'NR>1 {print $1}' training.csv | sort | uniq -c | sort -rn

# For Augmented Manifest: count per target
cat manifest.jsonl | python3 -c "
import sys, json
from collections import Counter
counts = Counter()
for line in sys.stdin:
    obj = json.loads(line)
    targets = obj.get('target', [])
    if isinstance(targets, str):
        targets = [targets]
    for t in targets:
        counts[t] += 1
for label, count in counts.most_common():
    print(f'{count:6d}  {label}')
"
```

### Handling class imbalance

- **Oversample minority classes:** duplicate minority-class documents
  (add slight variations to avoid exact duplicates).
- **Undersample majority classes:** randomly sample from majority
  classes to match the minority count (loses data).
- **Collect more data:** the best solution if feasible.
- **Merge similar classes:** if two classes are semantically close,
  merge them to increase per-class volume.

## Terraform examples

```hcl
# Comprehend document classifier (multi-class, CSV)
resource "aws_comprehend_document_classifier" "ticket" {
  name = "support-ticket-classifier"
  data_format = "COMPREHEND_CSV"

  input_data_config {
    s3_uri = "s3://${aws_s3_bucket.training.bucket}/comprehend/training/training.csv"
  }

  language_code = "en"

  document_classifier_config {
    mode = "MULTI_CLASS"
  }

  role_arn = aws_iam_role.comprehend_training.arn

  model_kms_key_id  = aws_kms_key.comprehend.arn
  volume_kms_key_id = aws_kms_key.comprehend.arn

  tags = {
    Environment = "production"
    Team        = "support"
  }
}

# Real-time endpoint
resource "aws_comprehend_endpoint" "ticket" {
  endpoint_name         = "ticket-endpoint"
  model_arn             = aws_comprehend_document_classifier.ticker.arn
  desired_inference_units = 1

  data_access_role_arn = aws_iam_role.comprehend_endpoint.arn

  tags = {
    Environment = "production"
  }
}
```

## Step 2 — Training data format (moved from SKILL.md)

**CSV format (line-level):**

```csv
label,text
billing,"I need a refund for my last invoice"
technical,"The API returns a 500 error"
```

Column 1 = label, column 2 = document text (inline). For multi-label,
pipe-separate labels: `billing|technical,"..."`.

**Augmented Manifest format (from Ground Truth):**

```json
{"source":"The invoice amount is incorrect","target":"billing"}
{"source":"The server is down","target":"technical"}
```

`source` = document text, `target` = label. For multi-label, `target`
is an array: `"target":["billing","technical"]`. Used when labeling is
done via SageMaker Ground Truth.

**Native PDF mode training data:**

```json
{"source":"s3://my-bucket/training/doc1.pdf","target":"invoice"}
{"source":"s3://my-bucket/training/doc2.pdf","target":"contract"}
```

`source` = S3 URI to the PDF file. Augmented Manifest ONLY (no CSV for
Native PDF). PDF files must be in the same region.
