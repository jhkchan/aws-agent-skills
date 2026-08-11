---
name: comprehend-classifier-deployer
description: >-
  Provisions Amazon Comprehend custom document classifiers with
  production defaults: multi-class vs multi-label mode, training data
  formats (CSV + Augmented Manifest from Ground Truth), classifier
  input mode (PLAIN_TEXT vs Native PDF), training job
  (create-document-classifier), evaluation metrics (precision, recall,
  F1), endpoint deployment for real-time inference with auto-scaling,
  batch inference jobs, KMS encryption for model artifacts and volume,
  VPC endpoint for private inference, IAM roles for training and
  deployment, model versioning, cost per training and inference hour.
  Emits a READY_TO_DEPLOY checklist with verification commands. Use
  when training a custom classifier, deploying a Comprehend endpoint,
  running batch classification, or choosing multi-class vs multi-label.
  Triggers: Comprehend custom classifier, document classifier training,
  multi-class multi-label, Comprehend endpoint, augmented manifest,
  native PDF classifier, batch inference.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with comprehend
  access (create-document-classifier, describe-document-classifier,
  create-endpoint, describe-endpoint, start-topics-detection-job), iam
  (create-role, attach-role-policy), kms (create-key), and ec2
  (create-vpc-endpoint). Works with Terraform
  aws_comprehend_document_classifier / aws_comprehend_endpoint resources
  and CloudFormation AWS::Comprehend::DocumentClassifier templates.
keywords:
  - aws
  - comprehend
  - document classifier
  - custom classifier
  - multi-class
  - multi-label
  - augmented manifest
  - native pdf
  - endpoint
  - batch inference
  - kms encryption
  - vpc endpoint
  - model evaluation
  - precision recall f1
  - cloudops
  - deploy
  - ai-ml
tags:
  - aws
  - comprehend
  - document-classifier
  - nlp
  - machine-learning
  - deploy
  - ai-ml
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - comprehend
    - document-classifier
    - nlp
    - machine-learning
    - deploy
    - ai-ml
  dependencies:
    - aws-orchestrator
  keywords:
    - comprehend custom classifier
    - document classifier training
    - multi-class classifier
    - multi-label classifier
    - comprehend endpoint deployment
    - augmented manifest training data
    - native PDF classifier
    - batch classification job
    - comprehend KMS encryption
    - comprehend VPC endpoint
  when_to_use: >-
    Invoke when the user wants to train an Amazon Comprehend custom
    document classifier (multi-class or multi-label), prepare training
    data in CSV or Augmented Manifest format, choose between plain text
    and native PDF input mode, deploy a real-time inference endpoint,
    run a batch classification job, configure KMS encryption for model
    artifacts, set up a VPC endpoint for private inference, define IAM
    roles for training and deployment, or evaluate model metrics
    (precision, recall, F1). Do NOT invoke for Comprehend pre-trained
    APIs (KeyPhraseExtraction, Sentiment), Comprehend Custom Entity
    Recognition, or Comprehend Topic Modeling (unsupervised).
---

# Comprehend Classifier Deployer

An AWS CloudOps agent skill that provisions Amazon Comprehend custom
document classifiers with correct defaults. The skill walks the operator
through multi-class vs multi-label selection, training data format
(CSV line-level vs Augmented Manifest from Ground Truth), classifier
input mode (PLAIN_TEXT vs Native PDF), training job submission, model
evaluation metrics, endpoint vs batch inference cost trade-off, KMS
encryption, VPC endpoint for private inference, IAM role scoping, model
versioning, and auto-scaling, captures classification requirements and
training data readiness, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

Comprehend custom classifier, document classifier training, multi-class
classifier, multi-label classifier, Comprehend endpoint, augmented
manifest, native PDF classifier, batch inference job, Comprehend KMS,
Comprehend VPC endpoint, classify documents.

## STRICT output contract

When this skill is invoked with a Comprehend classifier provisioning
request (train a classifier, deploy an endpoint, run batch inference,
configure encryption, set up VPC access, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`COMPREHEND_CLASSIFIER:`, `VERDICT:`, `CHECKLIST:`, and
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
| Step 1 — Multi-class vs multi-label | Classification mode decision |
| Step 2 — Training data format | CSV vs Augmented Manifest |
| Step 3 — Classifier input mode (PLAIN_TEXT vs Native PDF) | Document format decision |
| Step 4 — Training job (create-document-classifier) | Provisioning step |
| Step 5 — Model evaluation metrics | Precision, recall, F1 |
| Step 6 — Endpoint deployment and auto-scaling | Real-time inference |
| Step 7 — Batch inference job | Asynchronous classification |
| Step 8 — KMS encryption and VPC endpoint | Security and privacy |
| Step 9 — IAM roles and versioning | Permissions and lifecycle |
| Step 10 — Cost and recent features | Budget and latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/training-data-and-modes.md | Training data detail |
| references/endpoint-and-security.md | Endpoint + security detail |

## Mindset

**One-line takeaway:** A Comprehend custom classifier learns to assign
documents to categories you define. Multi-class assigns ONE label per
document; multi-label assigns ZERO or MORE labels per document. The
training data needs at least 50 documents per class for meaningful
results. Real-time endpoints charge per hour (whether or not you
classify); batch jobs charge per document processed.

Three misconceptions dominate Comprehend classifier misdesign at
provisioning time:

- **"Multi-class and multi-label are interchangeable."** They are not.
  Multi-class is for mutually exclusive categories (a support ticket is
  "billing" OR "technical" OR "general" — exactly one). Multi-label is
  for overlapping categories (a news article can be "politics" AND
  "economy" AND "world" simultaneously). Choosing the wrong mode
  degrades accuracy: multi-class forces one label when the content
  spans multiple; multi-label produces diffuse, low-confidence scores
  when categories are truly exclusive.

- **"50 documents per class is a guideline, not a hard minimum."** It
  is effectively a hard minimum. Below 50 documents per class, the
  model cannot learn discriminative patterns. AWS documentation
  recommends a minimum of 50; in practice, 200+ per class produces
  noticeably better metrics. With fewer than 50, the training job may
  complete but evaluation metrics (precision, recall, F1) will be poor.

- **"Endpoint and batch have similar cost profiles."** They do not. A
  real-time endpoint charges per hour for the entire time it is
  IN_SERVICE — even if zero documents are classified. For sporadic or
  batch workloads, the endpoint cost dwarfs the inference cost. Batch
  jobs charge per document processed with no idle cost.

## Configuration dependency graph (novel heuristic)

Comprehend classifier configurations are NOT independent. The training
data format determines the input config. The input mode (PLAIN_TEXT vs
Native PDF) constrains the training data source. The endpoint requires
a trained model. KMS and VPC config apply at both training and
inference time. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Training data (S3) | S3 bucket exists; CSV or Augmented Manifest format | CSV with wrong column count fails silently (error in job log); Augmented Manifest missing `source`/`target` fails | the training job |
| Training job (create-document-classifier) | training data S3 path; IAM role with comprehend + S3 read; KMS key if encrypting | job takes 30-90 min; status TRAINED or FAILED; mode is IMMUTABLE after creation | a model version (ARN) |
| Model evaluation | training job TRAINED | metrics (precision, recall, F1, accuracy) in describe-document-classifier; macro avg is headline metric | confidence in deployment |
| Endpoint (create-endpoint) | trained model ARN; endpoint name unique; IAM role | charges per hour from IN_SERVICE; auto-scaling needs CloudWatch + Application Auto Scaling | real-time inference |
| Batch inference | trained model ARN; input S3 path; output S3 path; IAM role | charges per document; output is JSONL in S3; no endpoint needed | asynchronous classification at scale |
| KMS encryption | KMS key ARN; IAM role with kms:Decrypt + kms:GenerateDataKey | encrypts model artifacts at rest AND EBS volume during training | data-at-rest protection |
| VPC endpoint | VPC with private subnets; route table with VPC endpoint entry; SG allowing 443 | inference calls stay private (no internet gateway); training can also run in VPC | private inference path |
| IAM role (training) | trust policy for comprehend.amazonaws.com; s3:GetObject + kms:Decrypt | overly broad permissions (s3:*) are a security risk; scope to training data bucket | training job execution |
| Model versioning | each create-document-classifier creates a new version | versions are IMMUTABLE; latest is default; specify version suffix for rollback | rollback capability |

**The endpoint-vs-batch-cost row is the one a baseline model misses.**
A baseline model picks endpoint because it sounds like the "production"
choice. The correct heuristic recognizes that endpoint charges per hour
regardless of utilization. For low-frequency workloads, batch is
dramatically cheaper.

**Cross-dependency gotchas:**
- Training data format and input mode are coupled. PLAIN_TEXT mode
  expects CSV with text columns OR Augmented Manifest with text
  `source`. Native PDF mode expects S3 paths to PDF files in Augmented
  Manifest format only — CSV is NOT supported for Native PDF.
- KMS encryption at training time and endpoint time are independent.
  Encrypting training artifacts does NOT automatically encrypt the
  endpoint. Configure KMS at both stages.
- VPC endpoint for Comprehend applies to API calls (inference from
  within the VPC). To run the training job in a VPC, specify
  `VpcConfig` in create-document-classifier.
- Auto-scaling for the endpoint requires a CloudWatch metric
  (ApproximateBacklogSize) and target tracking policy. Without it, the
  endpoint runs at a fixed instance count.

## Expert heuristic: multi-class vs multi-label classification choice

A baseline model says "use multi-class." The correct heuristic
recognizes that the choice depends on whether categories are mutually
exclusive.

```text
Classification mode decision:
  ├── Are categories mutually exclusive?
  │     ├── YES (a ticket is "billing" OR "technical" — exactly one)
  │     │     → MULTI-CLASS (DocumentClassifierConfig: mode = MULTI_CLASS)
  │     │     Training data: one label per document
  │     │     Output: top class + confidence score
  │     └── NO (an article can be "politics" AND "economy")
  │           → MULTI-LABEL (DocumentClassifierConfig: mode = MULTI_LABEL)
  │           Training data: one or more labels per document
  │           Output: per-class scores with independent thresholds
  └── Common mistake: using multi-class for overlapping categories
        → forces one label, misses secondary categories
        → degrades recall on multi-category documents
```

**Key implication:** the mode is set at training time and is IMMUTABLE.
You cannot change from multi-class to multi-label without retraining
from scratch. Choose correctly before preparing training data, because
the data format differs between modes.

## Expert heuristic: training data volume (minimum 50 docs/class)

A baseline model says "upload the CSV and train." The correct heuristic
verifies minimum data volume per class before submitting the training
job.

```text
Training data readiness check:
  For EACH class in the label set:
    ├── Count documents labeled with this class
    ├── < 50 documents → BLOCK (PREREQUISITES_MISSING)
    ├── 50-200 documents → CAUTION (trainable, moderate metrics)
    ├── 200-1000 documents → GOOD (suitable for production)
    └── 1000+ documents → EXCELLENT (production-grade)

  Also check class balance:
    ├── Ratio of largest to smallest class < 10:1 → balanced
    └── Ratio > 10:1 → imbalanced (oversample or collect more data)
```

**Key implication:** the 50-doc minimum is per class, not total. A
5-class classifier with 200 total documents is fine only if each class
has at least 40 (200/5 = 40 < 50 — actually NOT fine). Verify per-class
counts, not just total.

## Expert heuristic: endpoint vs batch cost trade-off

A baseline model says "deploy an endpoint for production." The correct
heuristic evaluates cost based on inference frequency.

```text
Endpoint vs batch decision:
  ├── Real-time, sub-second latency (user-facing app, API)
  │     → ENDPOINT: ~$0.05-$0.50/hr × 24/7/365
  │     Example: ml.m5.xlarge = ~$0.50/hr = ~$365/month
  ├── Periodic batch (nightly, hourly bulk)
  │     → BATCH: ~$0.0001 per 100 chars, no idle cost
  │     Example: 100k docs × 500 chars = ~$50/batch
  └── Sporadic, low-volume (< 1000 docs/day)
        → BATCH (cheaper than endpoint at low volume)
```

**Key implication:** endpoint cost is dominated by uptime, not
inference volume. If the endpoint is IN_SERVICE for 730 hours/month,
you pay for 730 hours regardless of how many documents you classify.
Batch jobs have zero idle cost.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Training data in S3 | Comprehend reads training data from S3 | `aws s3 ls s3://<bucket>/<prefix>/` |
| Minimum 50 docs/class | Below 50, the model cannot learn | Count per-class lines in CSV or manifest |
| S3 bucket in same region | Comprehend is regional; data must be in-region | `aws s3api get-bucket-location --bucket <bucket>` |
| IAM role for training | Comprehend assumes this role to read S3 | `aws iam get-role --role-name <role>` |
| KMS key (if encrypting) | Encrypts model artifacts and training volume | `aws kms describe-key --key-id <key-id>` |
| VPC subnets (if VPC training) | Training job runs in specified subnets | `aws ec2 describe-subnets --subnet-ids <ids>` |
| Label set defined | Classes/categories must be enumerated | Verify label values in training data |
| Language code | en, es, fr, de, it, pt, ar, hi, ja, ko, zh, zh-TW | Confirm language in classifier config |

## Step 1 — Multi-class vs multi-label

| Feature | Multi-class | Multi-label |
|---|---|---|
| Labels per document | Exactly ONE | ZERO or MORE |
| Training data | One label per row: `label,text` | Multiple labels: `label1\|label2,text` |
| Output | Top class + confidence | Per-class score with independent threshold |
| Use case | Ticket routing, sentiment bins | Topic tagging, multi-category content |
| Metrics | Accuracy, macro-F1, per-class precision/recall | Hamming loss, micro-F1, per-class precision/recall |
| Min docs/class | 50 | 50 (per individual label) |

**Common mistake:** using multi-label for a use case that is actually
multi-class. The model learns to assign multiple labels to documents
that should have one, producing noisy predictions.

## Step 2 — Training data format

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

## Step 3 — Classifier input mode (PLAIN_TEXT vs Native PDF)

| Feature | PLAIN_TEXT | Native PDF / Native DOC |
|---|---|---|
| Input | CSV inline text or Augmented Manifest with text | Augmented Manifest with S3 URI to PDF/DOC |
| Document support | Text only | Multi-page PDF, Word, images (with Textract) |
| Max document size | 10 KB per text | 500 MB per PDF, up to 2000 pages |
| Use case | Short text (tickets, reviews, emails) | Full documents (contracts, invoices, reports) |

**Common mistake:** using PLAIN_TEXT for PDF documents by extracting
text first. This loses layout information that Native PDF mode uses for
classification. Native PDF leverages visual layout features (tables,
headers, formatting) that plain text extraction discards.

## Step 4 — Training job (create-document-classifier)

Submit the training job. Takes 30-90 minutes depending on data volume.

```bash
CLASSIFIER_ARN=$(aws comprehend create-document-classifier \
  --document-classifier-name "support-ticket-classifier" \
  --data-format COMPREHEND_CSV \
  --input-data-config S3Uri=s3://my-bucket/comprehend/training/training.csv \
  --document-classifier-config "Mode=MULTI_CLASS,LanguageCode=en" \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendRole \
  --region us-east-1 \
  --query 'DocumentClassifierArn' --output text)
```

**With KMS encryption and VPC config:**

```bash
CLASSIFIER_ARN=$(aws comprehend create-document-classifier \
  --document-classifier-name "secure-classifier" \
  --data-format COMPREHEND_CSV \
  --input-data-config S3Uri=s3://my-bucket/comprehend/training/training.csv \
  --document-classifier-config "Mode=MULTI_CLASS,LanguageCode=en" \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendRole \
  --model-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --volume-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --vpc-config '{"SecurityGroupIds":["sg-abc123"],"Subnets":["subnet-aaa","subnet-bbb"]}' \
  --region us-east-1 \
  --query 'DocumentClassifierArn' --output text)
```

For Native PDF mode, add `--input-type NATIVE_PDF_DOCUMENTS` and use
Augmented Manifest format in the input S3 path. For multi-label,
change Mode to `MULTI_LABEL`.

**Monitor training status:**

```bash
aws comprehend describe-document-classifier \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --query 'DocumentClassifierProperties.Status' \
  --region us-east-1
# Expected: TRAINING → TRAINED (or FAILED)
```

## Step 5 — Model evaluation metrics

After training completes, evaluation metrics are available in
describe-document-classifier.

```bash
aws comprehend describe-document-classifier \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --query 'DocumentClassifierProperties.EvaluationMetrics' \
  --region us-east-1
```

| Metric | What it means | Production target |
|---|---|---|
| Accuracy | Overall correctness (multi-class) | > 0.80 |
| Precision (macro) | Average per-class precision | > 0.75 |
| Recall (macro) | Average per-class recall | > 0.75 |
| F1 (macro) | Harmonic mean, treats all classes equally | > 0.75 |
| F1 (micro) | Aggregate F1 weighted by class size | Compare with macro to detect imbalance |

**Interpreting:** macro-F1 much lower than micro-F1 = minority classes
underperforming. Below 0.60 F1: collect more data or re-evaluate the
classification scheme (too many classes? ambiguous labels?).

## Step 6 — Endpoint deployment and auto-scaling

Deploy a real-time inference endpoint for sub-second classification.

```bash
ENDPOINT_ARN=$(aws comprehend create-endpoint \
  --endpoint-name "ticket-classifier-endpoint" \
  --model-arn "$CLASSIFIER_ARN" \
  --desired-inference-units 1 \
  --data-access-role-arn arn:aws:iam::123456789012:role/ComprehendEndpointRole \
  --region us-east-1 \
  --query 'EndpointArn' --output text)
```

**Verify endpoint status:**

```bash
aws comprehend describe-endpoint \
  --endpoint-arn "$ENDPOINT_ARN" \
  --query 'EndpointProperties.Status' \
  --region us-east-1
# Expected: CREATING → IN_SERVICE
```

**Classify a document (real-time):**

```bash
aws comprehend classify-document \
  --endpoint-arn "$ENDPOINT_ARN" \
  --text "I need a refund for invoice #12345" \
  --region us-east-1
```

**Auto-scaling (Application Auto Scaling):**

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-classifier-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --min-capacity 1 --max-capacity 5

aws application-autoscaling put-scaling-policy \
  --policy-name "comprehend-scaling" \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-classifier-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":50.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ComprehendApproximateBacklogSize"},"ScaleInCooldown":300,"ScaleOutCooldown":60}'
```

## Step 7 — Batch inference job

Run asynchronous classification on documents in S3.

```bash
JOB_ID=$(aws comprehend classify-documents \
  --job-name "batch-classify-2026-08" \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --input-data-config S3Uri=s3://my-bucket/comprehend/input/ \
  --output-data-config S3Uri=s3://my-bucket/comprehend/output/ \
  --data-access-role-arn arn:aws:iam::123456789012:role/ComprehendBatchRole \
  --region us-east-1 \
  --query 'JobId' --output text)
```

**Monitor batch job:**

```bash
aws comprehend describe-document-classification-job \
  --job-id "$JOB_ID" \
  --query 'DocumentClassificationJobProperties.JobStatus' \
  --region us-east-1
# Expected: SUBMITTED → IN_PROGRESS → COMPLETED (or FAILED)
```

Batch output: JSONL files in the output S3 path, one classification
result per line. Use a unique output prefix per batch run to avoid
overwriting previous results.

## Step 8 — KMS encryption and VPC endpoint

**KMS encryption:** use `--model-kms-key-id` for model artifacts and
`--volume-kms-key-id` for the EBS volume during training. The IAM role
must have `kms:Decrypt` and `kms:GenerateDataKey` on the key.

**VPC endpoint for private Comprehend API access:**

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.comprehend \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-comprehend \
  --region us-east-1
```

This enables inference calls from within the VPC to stay on the AWS
network (no internet gateway needed). The security group must allow
inbound 443 from the calling resource.

**VPC config for training job:** add `--vpc-config` to create-document-
classifier to run training entirely within a VPC.

## Step 9 — IAM roles and versioning

**Training role trust policy** must allow `comprehend.amazonaws.com` to
assume. Permissions: `s3:GetObject` and `s3:ListBucket` on the training
data bucket, plus `kms:Decrypt`/`kms:GenerateDataKey` on the KMS key
(if encrypting). Scope to the specific bucket — avoid `s3:*`.

**Endpoint role** only needs `comprehend:Detect*` permissions. It does
NOT need S3 access. Over-privileged endpoint roles are a security risk.

**Versioning:** each `create-document-classifier` call with the same
name creates a new immutable version. The latest version is the
default. To use a specific version, include the version suffix in the
ARN. Old versions incur storage cost — delete unused versions.

```bash
# List all versions
aws comprehend list-document-classifiers \
  --query 'DocumentClassifierPropertiesList[*].{Name:DocumentClassifierName,Version:Version,Status:Status}' \
  --region us-east-1

# Delete a specific version
aws comprehend delete-document-classifier \
  --document-classifier-arn "arn:aws:comprehend:us-east-1:123456789012:document-classifier/my-classifier/version/1"
```

## Step 10 — Cost and recent features

**Cost summary (us-east-1):**

| Resource | Cost | Notes |
|---|---|---|
| Training job | ~$0.005 per 1,000 chars for training | Charged per training run |
| Real-time endpoint | ~$0.05-$0.50 per inference-unit-hour | Charged for IN_SERVICE time, 24/7 |
| Batch inference | ~$0.0001 per 100 chars processed | Charged per document, no idle cost |
| Model artifact storage | ~$0.023 per GB/month (S3) | Per version, accumulates |

**Cost optimization:** use batch for low-volume workloads; delete old
model versions; use auto-scaling to scale down during low-traffic;
reduce label count for multi-label classifiers.

**Recent features (2023-2026):**

- **Native PDF classification (2023-2024):** Comprehend supports
  classifying multi-page PDF documents natively using layout and visual
  features in addition to text. Training data as S3 URIs in Augmented
  Manifest format.
- **Auto-scaling for endpoints (2023-2024):** Application Auto Scaling
  supports Comprehend endpoints via ApproximateBacklogSize metric.
- **VPC training support (2024-2025):** Training jobs can run entirely
  within a VPC via VpcConfig in create-document-classifier.
- **Volume KMS encryption (2024-2025):** `--volume-kms-key-id`
  parameter encrypts the EBS volume during training.
- **Multi-label threshold tuning (2025-2026):** Multi-label output
  includes per-class confidence scores that can be independently
  thresholded at inference time without retraining.
- **Terraform provider maturity (2024-2025):** Terraform
  `aws_comprehend_document_classifier` and `aws_comprehend_endpoint`
  now support multi-label, Native PDF, VPC config, and both KMS params.

## NEVER do these things

1. **NEVER use multi-class mode for overlapping categories.** If a
   document can belong to multiple categories simultaneously, multi-
   label is the correct mode. Multi-class forces one label, missing
   secondary categories and degrading recall.

2. **NEVER submit a training job with fewer than 50 documents per
   class.** The model cannot learn discriminative patterns below 50.
   Collect more labeled data or merge similar classes before training.

3. **NEVER deploy an endpoint for a periodic batch workload.** The
   endpoint charges per hour whether or not you classify documents.
   For nightly or hourly batch processing, use batch inference jobs.

4. **NEVER use PLAIN_TEXT mode for multi-page PDF documents.**
   PLAIN_TEXT loses layout information. Use Native PDF mode which
   leverages visual layout features for better accuracy.

5. **NEVER use the same IAM role for training and endpoint inference.**
   The training role needs S3 read + KMS decrypt. The endpoint role
   only needs comprehend inference permissions. Over-privileged
   endpoint roles are a security risk.

6. **NEVER forget to encrypt model artifacts with KMS.** Without
   `--model-kms-key-id`, model artifacts use an AWS-managed key you
   cannot control or audit. Use a customer-managed CMK for
   compliance-sensitive workloads.

7. **NEVER assume the training job succeeded without checking status.**
   Training jobs can fail (status: FAILED). Always check
   describe-document-classifier for TRAINED and review metrics before
   deploying.

8. **NEVER delete old model versions without verifying endpoint
   references.** If an endpoint points to an older version, deleting
   that version breaks inference. Check endpoint model ARN first.

9. **NEVER ignore class imbalance.** If one class has 1000 documents
   and another has 50, the model biases toward the majority class.
   Check macro vs micro F1 gap and oversample minority classes.

10. **NEVER use CSV format with Native PDF mode.** Native PDF requires
    Augmented Manifest with S3 URIs as the `source` field. CSV is only
    for PLAIN_TEXT mode.

## Output format

```text
COMPREHEND_CLASSIFIER: <classifier-name> (<mode>, <input-mode>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Classifier name: <name>
  [✓|✗] Classification mode: MULTI_CLASS | MULTI_LABEL
  [✓|✗] Input mode: PLAIN_TEXT | NATIVE_PDF
  [✓|✗] Training data: s3://<bucket>/<path> (<format>, <doc-count>)
  [✓|✗] Docs per class: min=<n> (class=<label>) — PASS (≥50) | FAIL (<50)
  [✓|✗] Class balance: ratio=<max>:<min> — balanced | imbalanced
  [✓|✗] Language code: <code>
  [✓|✗] IAM role (training): <role-arn>
  [✓|✗] KMS (model): <key-arn> | AWS-managed (no CMK)
  [✓|✗] KMS (volume): <key-arn> | AWS-managed (no CMK)
  [✓|✗] VPC config: subnets=<subnet-list>, sg=<sg-id> | none
  [✓|✗] Inference mode: ENDPOINT (<instance>, <units>) | BATCH
  [✓|✗] Endpoint ARN: <endpoint-arn> (if endpoint)
  [✓|✗] Auto-scaling: min=<n>, max=<n>, target=<metric> | none
  [✓|✗] Model ARN: <classifier-arn> (version <n>)
  [✓|✗] Evaluation: accuracy=<n>, macro-F1=<n>, micro-F1=<n>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws comprehend describe-document-classifier --document-classifier-arn <arn> --region <region>
  aws comprehend describe-endpoint --endpoint-arn <arn> --region <region> (if endpoint)
  aws comprehend list-document-classifiers --region <region>
```

### Worked example — multi-class, PLAIN_TEXT, endpoint deployment

```text
COMPREHEND_CLASSIFIER: support-ticket-classifier (MULTI_CLASS, PLAIN_TEXT)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Classifier name: support-ticket-classifier
  [✓] Classification mode: MULTI_CLASS
  [✓] Input mode: PLAIN_TEXT
  [✓] Training data: s3://my-bucket/comprehend/training/training.csv (CSV, 5000 docs)
  [✓] Docs per class: min=850 (class=general) — PASS (≥50)
  [✓] Class balance: ratio=1.7:1 — balanced
  [✓] Language code: en
  [✓] IAM role (training): arn:aws:iam::123456789012:role/ComprehendTrainingRole
  [✓] KMS (model): arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] KMS (volume): arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] VPC config: none (internet-routed training)
  [✓] Inference mode: ENDPOINT (1 inference unit)
  [✓] Endpoint ARN: arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-endpoint
  [✓] Auto-scaling: min=1, max=5, target=ApproximateBacklogSize=50
  [✓] Model ARN: arn:aws:comprehend:us-east-1:123456789012:document-classifier/support-ticket-classifier/version/1
  [✓] Evaluation: accuracy=0.87, macro-F1=0.84, micro-F1=0.86
  [✓] Tags: Environment=production, Team=support
VERIFICATION_COMMANDS:
  aws comprehend describe-document-classifier --document-classifier-arn arn:aws:comprehend:us-east-1:123456789012:document-classifier/support-ticket-classifier/version/1 --region us-east-1
  aws comprehend describe-endpoint --endpoint-arn arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-endpoint --region us-east-1
  aws comprehend list-document-classifiers --region us-east-1
```

## Error handling

### Training job FAILED
- Check CloudWatch Logs (log group: `/aws/comprehend/<classifier-name>`).
- Common causes: training data format error (wrong column count, invalid
  JSON in Augmented Manifest), S3 access denied, KMS access denied.
- Fix the data or IAM policy, then resubmit (creates a new version).

### Low evaluation metrics (F1 < 0.60)
- Insufficient training data per class. Collect more labeled documents.
- Ambiguous or overlapping class definitions. Re-evaluate the label set.
- Class imbalance. Oversample minority classes or collect more data.

### Endpoint not scaling
- Verify auto-scaling target tracking policy is attached.
- Check CloudWatch alarm for ApproximateBacklogSize exists.
- ScaleInCooldown may be too aggressive; increase to avoid flapping.

### VPC endpoint inference fails
- Security group must allow inbound 443 from the calling resource.
- Route table must include the VPC endpoint entry.
- DNS resolution must be enabled on the VPC.

## Domain

AWS CloudOps / Amazon Comprehend Custom Document Classifier Training,
Evaluation, and Inference Deployment.

## AWS documentation

- **Comprehend Custom Classification** — https://docs.aws.amazon.com/comprehend/latest/dg/custom-document-classifier.html
- **Training a custom classifier** — https://docs.aws.amazon.com/comprehend/latest/dg/training-classifier-model.html
- **Multi-class vs multi-label** — https://docs.aws.amazon.com/comprehend/latest/dg/training-classifier-model.html#multi-class
- **Augmented Manifest format** — https://docs.aws.amazon.com/comprehend/latest/dg/prep-classifier-data.html#augmented-manifest
- **Native PDF classification** — https://docs.aws.amazon.com/comprehend/latest/dg/native-pdf-doc-classifier.html
- **Endpoint deployment** — https://docs.aws.amazon.com/comprehend/latest/dg/using-endpoints.html
- **Batch inference** — https://docs.aws.amazon.com/comprehend/latest/dg/getting-started-custom-classification.html#batch-classification
- **KMS encryption** — https://docs.aws.amazon.com/comprehend/latest/dg/security_iam_id-based-policy-examples.html#encryption
- **VPC for Comprehend** — https://docs.aws.amazon.com/comprehend/latest/dg/vpc-comprehend.html
- **Auto-scaling endpoints** — https://docs.aws.amazon.com/comprehend/latest/dg/auto-scaling.html
