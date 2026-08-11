---
name: rekognition-collection-deployer
description: >-
  Provisions Amazon Rekognition face collections and detection pipelines
  with production defaults: collection creation (create-collection), face
  indexing (index-faces, FaceId generation), face search (search-faces,
  search-faces-by-image), similarity threshold tuning (80%+ for
  production matching), stream processor for video analysis (Kinesis
  stream integration, shard-level parallelism), celebrity recognition,
  content moderation (unsafe content detection), text in image, label
  detection, PPE detection, custom labels model training and deployment,
  KMS encryption, IAM roles for Rekognition, SNS notification for async
  jobs, cost per image/video analysis, rate limiting (TPS), and
  collection size limits. Emits a READY_TO_DEPLOY checklist with
  verification commands. Use when creating a Rekognition collection,
  indexing faces, searching faces by image or FaceId, setting up a
  stream processor for video, detecting labels or text, running content
  moderation, detecting PPE, training custom labels, or configuring
  celebrity recognition. Triggers: create rekognition collection, index
  faces, search faces by image, face search similarity threshold,
  rekognition stream processor, celebrity recognition, content
  moderation, text in image detection, label detection, ppe detection,
  custom labels model training, rekognition kms encryption.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with rekognition
  access. Works with Terraform aws_rekognition_collection /
  aws_rekognition_stream_processor resources and CloudFormation
  AWS::Rekognition::Collection templates.
keywords:
  - aws
  - rekognition
  - face collection
  - face search
  - cloudops
  - deploy
  - provisioning
  - stream processor
  - celebrity recognition
  - content moderation
  - label detection
  - text detection
  - ppe detection
  - custom labels
  - kms encryption
tags:
  - aws
  - rekognition
  - face-collection
  - cloudops
  - deploy
  - ai-ml
  - provisioning
  - stream-processor
  - content-moderation
  - celebrity-recognition
  - label-detection
  - custom-labels
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
    - rekognition
    - face-collection
    - cloudops
    - deploy
    - ai-ml
    - provisioning
    - stream-processor
    - content-moderation
    - celebrity-recognition
    - label-detection
    - custom-labels
  dependencies:
    - aws-orchestrator
  keywords:
    - create rekognition collection
    - index faces
    - search faces by image
    - face search similarity threshold
    - rekognition stream processor
    - celebrity recognition
    - content moderation
    - text in image detection
    - label detection
    - ppe detection
    - custom labels model training
    - rekognition kms encryption
  when_to_use: >-
    Invoke when the user wants to create a Rekognition face collection,
    index faces into a collection, search faces by image or FaceId, set
    up a stream processor for video analysis, detect labels or text in
    images, run content moderation, detect PPE, train and deploy custom
    labels models, configure celebrity recognition, or integrate
    Rekognition with Kinesis, SNS, and KMS. Do NOT invoke for Amazon
    Textract (document analysis), Amazon Transcribe (speech-to-text),
    or Amazon Comprehend (NLP) — those are separate services.
---

# Rekognition Collection Deployer

An AWS CloudOps agent skill that provisions Amazon Rekognition face
collections and detection pipelines with correct defaults. The skill
walks the operator through collection creation, face indexing, face
search with similarity threshold tuning, stream processor configuration
for video analysis, content moderation, label and text detection, PPE
detection, celebrity recognition, custom labels model training, KMS
encryption, IAM roles, SNS notifications for async jobs, cost and rate
limit considerations, and collection size limits, captures detection
requirements, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Rekognition collection, index faces, search faces by image, face
search similarity threshold, Rekognition stream processor, celebrity
recognition, content moderation, text in image detection, label
detection, PPE detection, custom labels model training, Rekognition KMS
encryption.

## STRICT output contract

When this skill is invoked with a Rekognition-provisioning request
(create a collection, index faces, search faces, set up a stream
processor, detect labels/text/moderation/PPE, train custom labels, or a
partial configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `REKOGNITION:`, `VERDICT:`, `CHECKLIST:`, and
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
| Step 1 — Collection creation and size limits | Core collection model |
| Step 2 — Face indexing (FaceId generation) | Indexing faces |
| Step 3 — Face search by image and by FaceId | Face matching |
| Step 4 — Similarity threshold tuning | Production face matching |
| Step 5 — Stream processor for video analysis | Kinesis video integration |
| Step 6 — Celebrity recognition | Celebrity detection |
| Step 7 — Content moderation | Unsafe content detection |
| Step 8 — Text in image and label detection | Detection features |
| Step 9 — PPE detection | Safety compliance |
| Step 10 — Custom labels model training and deployment | Custom model lifecycle |
| Step 11 — KMS encryption and IAM roles | Security |
| Step 12 — SNS notifications for async jobs | Async job orchestration |
| Step 13 — Cost and rate limiting | Economics and TPS |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/face-search-and-threshold.md | Face search + threshold detail |
| references/stream-processor-and-async.md | Stream processor + async detail |

## Mindset

**One-line takeaway:** A Rekognition collection is a managed face
vector store. You create it, index faces into it (each face gets a
FaceId), and then search it by image or by FaceId. The similarity
threshold determines match strictness — 80%+ is production-grade. For
video analysis, the stream processor reads from a Kinesis stream and
writes face matches to another Kinesis stream with shard-level
parallelism.

Three misconceptions dominate Rekognition misdesign at provisioning
time:

- **"The default similarity threshold is fine."** The API default is
  80%, but many operators pass lower thresholds (50-60%) to get more
  matches. This produces false positives at scale. For production face
  matching, 80%+ is the minimum. Below 80%, expect significant false
  positive rates, especially as collection size grows.

- **"Collections scale infinitely."** A single collection supports up to
  50 million faces, but search latency degrades as face count grows. At
  1 million+ faces, consider partitioning by region or category into
  multiple collections. The TPS limit per collection is also a factor —
  index-faces and search-faces-by-image share the same TPS quota.

- **"The stream processor handles scaling."** The stream processor reads
  from Kinesis shards. Throughput is bounded by the number of shards.
  Shard-level parallelism is the scaling lever — more shards = more
  parallel face searches. A single shard limits the processor to one
  concurrent consumer.

## Configuration dependency graph (novel heuristic)

Rekognition configurations are NOT independent. The collection must
exist before faces are indexed. Faces must be indexed before they can be
searched. The stream processor needs BOTH a Kinesis input stream and a
Kinesis output stream. KMS encryption must be configured at collection
creation time (not retroactively). Custom labels models must be trained
before they can be started. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Collection | KMS key (if encrypted); IAM `rekognition:CreateCollection` | KMS encryption CANNOT be added after creation — must be set at create time | face indexing, face search |
| Face indexing | Collection exists; image in S3 or bytes; IAM `rekognition:IndexFaces` | FaceId is generated server-side; ExternalImageId is optional but recommended for traceability | face search by FaceId |
| Face search (by image) | Collection has indexed faces; IAM `rekognition:SearchFacesByImage` | similarity threshold below 80% produces false positives at scale | face matching results |
| Face search (by FaceId) | FaceId from prior index or search; IAM `rekognition:SearchFaces` | searches the same collection for similar faces to the given FaceId | face matching by ID |
| Stream processor | Kinesis input stream; Kinesis output stream; IAM role with Kinesis + Rekognition + S3 permissions; collection exists | shard count in the input stream determines parallelism; processor reads 1 shard at a time per consumer | real-time video face detection |
| Celebrity recognition | IAM `rekognition:RecognizeCelebrities` | works without a collection (uses built-in celebrity index) | celebrity detection results |
| Content moderation | IAM `rekognition:DetectModerationLabels` | works without a collection | unsafe content flags |
| Text in image | IAM `rekognition:DetectText` | works without a collection | detected text lines/words |
| Label detection | IAM `rekognition:DetectLabels` | works without a collection | scene/object labels |
| PPE detection | IAM `rekognition:DetectProtectiveEquipment` | DetectPPE requires image with persons; returns body part coverage | PPE compliance results |
| Custom labels model | S3 training data (images + manifest); IAM `rekognition:CreateProject` then train; dataset labeled | model MUST be started (start-project-version) after training; inference costs accrue per hour while running | custom label inference |
| KMS encryption | KMS key with proper key policy for Rekognition service | CANNOT be added after collection creation — MUST be set at create time | encryption at rest |
| SNS notification | SNS topic with Rekognition access; IAM `rekognition:Start*` with NotificationChannel | only async operations support SNS (StartFaceSearch, StartLabelDetection, StartContentModeration, StartTextDetection) | async job completion callbacks |
| Async job (Start*) | S3 video/image input; SNS topic (optional); IAM `rekognition:Start*` and `rekognition:Get*` | results retrieved via Get* operations; JobId required for retrieval | batch video/image analysis |

**The KMS-at-creation row is the one a baseline model misses.** KMS
encryption cannot be added to an existing collection. If encryption is
required (compliance, GDPR, HIPAA), the KMS key ID MUST be specified at
`create-collection` time. Re-creating an encrypted collection means
re-indexing all faces. The procedure below forces an explicit decision
on encryption before creation.

**Cross-dependency gotchas:**
- The stream processor needs a Kinesis data stream (not a Kinesis Video
  Stream). The processor reads frames from the Kinesis data stream,
  where each record is a base64-encoded JPEG.
- Face indexing and face search share the same TPS quota. Heavy indexing
  can throttle search performance. Plan indexing during off-peak hours.
- Custom labels models incur hourly charges while running. Stop the
  model (`stop-project-version`) when not in use to avoid idle charges.
- SNS notifications only work with async (Start*) operations, not with
  synchronous (Detect*, Search*) operations.
- The stream processor's IAM role needs `kinesis:GetRecords` on the
  input stream, `kinesis:PutRecord` on the output stream, and
  `rekognition:SearchFaces` on the collection — all three.

## Expert heuristic: similarity threshold 80%+ for face matching

A baseline model says "search faces with the default threshold." The
correct heuristic recognizes that threshold tuning is the single most
important quality lever in production face matching.

```text
Similarity threshold guide:
  ├── 99%+   → near-exact match (high false-negative rate; use for
  │            identity verification, access control)
  ├── 90-99% → strict matching (low false-positive; use for badge
  │            systems, attendance)
  ├── 80-90% → production-grade (balanced; recommended default for
  │            most applications — this is the sweet spot)
  ├── 60-80% → loose matching (higher false-positive rate; use only
  │            for human-in-the-loop review)
  └── <60%   → NOT recommended (unreliable; false positives dominate)

Collection size impact on accuracy:
  ├── <10k faces      → 80% threshold is reliable
  ├── 10k-100k faces  → 80% threshold recommended; consider 85% for
  │                      tighter matching
  ├── 100k-1M faces   → 85%+ recommended; false positive rate rises
  ├── 1M-10M faces    → 90%+ recommended; consider collection
  │                      partitioning by region/category
  └── 10M+ faces      → MUST partition into multiple collections;
                          single-collection search degrades
```

**Key implication:** the similarity threshold is not a "set and forget"
parameter. As the collection grows, the threshold may need to increase
to maintain the same false-positive rate. Monitor search quality metrics
(match rate, false positive feedback) and adjust the threshold
accordingly.

## Expert heuristic: stream processor shard-level parallelism

The stream processor reads from Kinesis shards. Each shard is processed
by one consumer. More shards = more parallel face searches = higher
throughput.

```text
Stream processor throughput scaling:
  Input Kinesis stream shard count:
    ├── 1 shard  → ~1 MB/sec ingest, 1 concurrent face search
    ├── 4 shards → ~4 MB/sec ingest, 4 concurrent face searches
    └── N shards → N concurrent face searches (linear scaling)

  Shard-to-face-search mapping:
    Each shard delivers records → stream processor calls
    SearchFaces for each frame → face match written to output stream

  Output Kinesis stream:
    ├── Needs enough shards to absorb output rate
    └── If output is throttled, processor backs up and input lags

  Typical production setup:
    Input: 4-8 shards (camera feeds, frame rate ~1-5 fps per camera)
    Output: 2-4 shards (match results, smaller payload per record)
    Collection: partitioned by site/region if >1M faces
```

**Key implication:** the stream processor's throughput is NOT
configurable via the Rekognition API — it is determined entirely by the
input Kinesis stream's shard count. To scale video analysis throughput,
scale the Kinesis shards, not the processor configuration.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS region supports Rekognition | Not all regions support all Rekognition features | Check service availability in target region |
| KMS key (if encryption required) | KMS must be set at collection creation; cannot be added later | `aws kms describe-key --key-id <key-id>` |
| IAM role for stream processor | Stream processor needs Kinesis + Rekognition + S3 permissions | Verify role trust policy and permissions |
| Kinesis input stream (if stream processor) | Stream processor reads frames from Kinesis data stream | `aws kinesis describe-stream --stream-name <name>` |
| Kinesis output stream (if stream processor) | Match results written to output stream | `aws kinesis describe-stream --stream-name <name>` |
| S3 bucket for images/video (if async or indexing) | Index-faces and async operations read from S3 | `aws s3 ls s3://<bucket>` |
| SNS topic (if async notifications) | Async jobs send completion to SNS | `aws sns get-topic-attributes --topic-arn <arn>` |
| Collection size estimate | Affects threshold and partitioning decisions | Estimate face count to be indexed |
| Custom labels training data (if custom labels) | Needs labeled images + manifest in S3 | Verify S3 manifest.json exists |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Collection creation and size limits

A Rekognition collection is a managed vector index of face feature
vectors. Each collection can hold up to 50 million faces.

**Create a collection (no encryption):**

```bash
aws rekognition create-collection \
  --collection-id "employee-faces" \
  --region us-east-1
```

**Create a collection with KMS encryption:**

```bash
aws rekognition create-collection \
  --collection-id "employee-faces" \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd-1234 \
  --region us-east-1
```

**Critical:** KMS encryption CANNOT be added after creation. If
encryption is needed, specify `--kms-key-id` at creation time.

**Collection size limits:**

| Limit | Value | Notes |
|---|---|---|
| Max faces per collection | 50,000,000 | Partition for larger scale |
| Max collections per account | Determined by service quota | Default varies by region |
| Face image max size | 5 MB (S3); 5 MB (bytes) | JPEG or PNG only |
| Face image min size | 80x80 pixels | Smaller faces may not be detected |
| Max faces detected per image | Depends on image; up to 100+ | Each detected face gets a FaceId if indexed |

## Step 2 — Face indexing (FaceId generation)

Indexing faces adds them to the collection. Each indexed face gets a
unique FaceId (server-generated UUID).

**Index faces from an S3 image:**

```bash
aws rekognition index-faces \
  --collection-id "employee-faces" \
  --image '{"S3Object":{"Bucket":"my-face-bucket","Name":"employee-001.jpg"}}' \
  --external-image-id "employee-001" \
  --detection-attributes '["DEFAULT"]' \
  --max-faces 1 \
  --quality-filter "AUTO" \
  --region us-east-1
```

**Key parameters:**
- `--external-image-id`: Optional but recommended. Maps the FaceId to an
  external identifier (employee ID, user ID). Use for traceability.
- `--max-faces`: Limits the number of faces indexed from the image. Set
  to 1 for single-person photos to avoid indexing background faces.
- `--quality-filter`: `AUTO` (recommended), `LOW`, `MEDIUM`, `HIGH`, or
  `NONE`. Filters out low-quality faces.

**Response includes:**

```json
{
  "FaceRecords": [
    {
      "Face": {
        "FaceId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "BoundingBox": { "Width": 0.1, "Height": 0.2, "Left": 0.3, "Top": 0.4 },
        "ImageId": "ffffffff-0000-1111-2222-333333333333",
        "ExternalImageId": "employee-001"
      },
      "FaceDetail": { "Confidence": 99.9, ... }
    }
  ],
  "FaceModelVersion": "7.0",
  "OrientationCorrection": "ROTATE_0"
}
```

**Common mistake:** indexing without `--external-image-id`. Without it,
FaceIds are opaque UUIDs with no human-readable mapping.

## Step 3 — Face search by image and by FaceId

Rekognition supports two search modes: search by image (find matching
faces in the collection given a query image) and search by FaceId (find
faces similar to a known FaceId).

**Search faces by image:**

```bash
aws rekognition search-faces-by-image \
  --collection-id "employee-faces" \
  --image '{"S3Object":{"Bucket":"my-face-bucket","Name":"query.jpg"}}' \
  --face-match-threshold 80 \
  --max-faces 5 \
  --region us-east-1
```

**Search faces by FaceId:**

```bash
aws rekognition search-faces \
  --collection-id "employee-faces" \
  --face-id "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --face-match-threshold 80 \
  --max-faces 5 \
  --region us-east-1
```

**Key parameters:**
- `--face-match-threshold`: Minimum similarity (0-100). 80+ for
  production.
- `--max-faces`: Maximum matches to return.

**Response includes FaceMatches with Similarity (0-100):**

```json
{
  "SearchedFaceBoundingBox": { ... },
  "SearchedFaceConfidence": 99.98,
  "FaceMatches": [
    {
      "Similarity": 99.5,
      "Face": {
        "FaceId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "ExternalImageId": "employee-001"
      }
    }
  ],
  "FaceModelVersion": "7.0"
}
```

## Step 4 — Similarity threshold tuning

The similarity threshold is the single most important quality lever.
The default API threshold is 80%.

| Threshold | Use case | False positive rate | False negative rate |
|---|---|---|---|
| 99%+ | Identity verification, access control | Very low | High |
| 90-99% | Badge systems, attendance | Low | Low |
| 80-90% | Production face matching (recommended) | Moderate | Low |
| 60-80% | Human-in-the-loop review | High | Very low |
| <60% | NOT recommended | Very high | Near zero |

**Production recommendation:** start at 80%, monitor false positives,
and increase to 85-90% if the collection exceeds 100k faces.

## Step 5 — Stream processor for video analysis

The stream processor reads frames from a Kinesis data stream, searches
each frame against a collection, and writes face matches to a Kinesis
output stream.

**Create a stream processor:**

```bash
aws rekognition create-stream-processor \
  --name "camera-feed-processor" \
  --input '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-input"}}' \
  --output '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-output"}}' \
  --role-arn "arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole" \
  --settings '{"FaceSearch":{"CollectionId":"employee-faces","FaceMatchThreshold":85.0}}' \
  --regions-of-interest '[{"BoundingBox":{"Width":1.0,"Height":1.0,"Left":0.0,"Top":0.0}}]' \
  --data--processing-before-analysis '{"ConnectedHome":{"MinConnectedTimeInSeconds":1.0}}' \
  --region us-east-1
```

**Start the stream processor:**

```bash
aws rekognition start-stream-processor \
  --name "camera-feed-processor" \
  --start-selector '{"KVSStreamSelector":{"StartTimestamp":1630000000}}' \
  --stop-selector '{"MaxDurationInSeconds":3600}' \
  --region us-east-1
```

**Shard-level parallelism:** the input Kinesis stream's shard count
determines concurrent face searches. Scale shards to scale throughput.

```bash
# Check shard count
aws kinesis describe-stream-summary \
  --stream-name rekognition-input \
  --query 'StreamDescriptionSummary.NumberOfShards' \
  --region us-east-1
```

**Stream processor IAM role (trust policy):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "rekognition.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Stream processor IAM role (permissions):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "kinesis:DescribeStream",
        "kinesis:ListShards"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-input"
    },
    {
      "Effect": "Allow",
      "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-output"
    },
    {
      "Effect": "Allow",
      "Action": ["rekognition:SearchFaces", "rekognition:SearchFacesByImage"],
      "Resource": "arn:aws:rekognition:us-east-1:123456789012:collection/employee-faces"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-face-bucket/*"
    }
  ]
}
```

## Step 6 — Celebrity recognition

Celebrity recognition identifies celebrities in images. It uses a
built-in celebrity index (no collection needed).

```bash
aws rekognition recognize-celebrities \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"event-photo.jpg"}}' \
  --region us-east-1
```

Response includes `CelebrityFaces` (matched celebrities with name, ID,
confidence, URLs) and `UnrecognizedFaces`.

## Step 7 — Content moderation

Content moderation detects unsafe content (explicit, suggestive,
violence, etc.).

```bash
aws rekognition detect-moderation-labels \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"user-upload.jpg"}}' \
  --min-confidence 60 \
  --region us-east-1
```

**Async moderation (for video):**

```bash
JOB_ID=$(aws rekognition start-content-moderation \
  --video '{"S3Object":{"Bucket":"my-bucket","Name":"video.mp4"}}' \
  --min-confidence 60 \
  --notification-channel '{"SNSTopicArn":"arn:aws:sns:us-east-1:123456789012:rekognition-complete","RoleArn":"arn:aws:iam::123456789012:role/RekognitionSNSRole"}' \
  --region us-east-1 \
  --query 'JobId' --output text)

# Retrieve results
aws rekognition get-content-moderation \
  --job-id "$JOB_ID" \
  --region us-east-1
```

## Step 8 — Text in image and label detection

**Detect text:**

```bash
aws rekognition detect-text \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"signage.jpg"}}' \
  --filters '{"WordFilter":{"MinConfidence":90,"MinBoundingBoxHeight":0.005,"MinBoundingBoxWidth":0.005}}' \
  --region us-east-1
```

**Detect labels (scene/object detection):**

```bash
aws rekognition detect-labels \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"photo.jpg"}}' \
  --max-labels 50 \
  --min-confidence 75 \
  --features '["GENERAL_LABELS"]' \
  --settings '{"GeneralLabels":{"LabelInclusionFilters":["Person","Vehicle","Building"]}}' \
  --region us-east-1
```

## Step 9 — PPE detection

PPE detection identifies protective equipment (face cover, hand cover,
head cover) and whether persons are wearing them.

```bash
aws rekognition detect-protective-equipment \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"worksites.jpg"}}' \
  --required-equipment-types '["FACE_COVER","HAND_COVER","HEAD_COVER"]' \
  --region us-east-1
```

Response includes `Persons` with `BodyParts` and `EquipmentDetections`,
including confidence scores and `CoversBodyPart` boolean.

## Step 10 — Custom labels model training and deployment

Custom labels train a model on your specific images (e.g., industrial
defects, product logos).

**Create a project:**

```bash
aws rekognition create-project \
  --project-name "industrial-defects" \
  --region us-east-1
```

**Create a dataset (training):**

```bash
aws rekognition create-dataset \
  --dataset-source '{"GroundTruthManifest":{"S3Object":{"Bucket":"my-bucket","Name":"training/manifest.json"}}}' \
  --dataset-type TRAIN \
  --project-arn "arn:aws:rekognition:us-east-1:123456789012:project/industrial-defects/1234" \
  --region us-east-1
```

**Train the model:**

```bash
aws rekognition create-project-version \
  --project-arn "arn:aws:rekognition:us-east-1:123456789012:project/industrial-defects/1234" \
  --version-name "v1" \
  --output-config '{"S3Bucket":"my-bucket","S3KeyPrefix":"model-output/"}' \
  --training-data '{"Assets":[{"GroundTruthManifest":{"S3Object":{"Bucket":"my-bucket","Name":"training/manifest.json"}}}]}' \
  --testing-data '{"AutoCreate":true}' \
  --region us-east-1
```

**Start the model (inference):**

```bash
aws rekognition start-project-version \
  --project-version-arn "arn:aws:rekognition:us-east-1:123456789012:project/industrial-defects/v1/1234" \
  --min-inference-units 1 \
  --region us-east-1
```

**Critical:** custom labels models incur hourly charges while running.
Stop the model when not in use:

```bash
aws rekognition stop-project-version \
  --project-version-arn "arn:aws:rekognition:us-east-1:123456789012:project/industrial-defects/v1/1234" \
  --region us-east-1
```

## Step 11 — KMS encryption and IAM roles

### KMS encryption

KMS encryption for collections MUST be configured at creation time.

```bash
aws rekognition create-collection \
  --collection-id "secure-faces" \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd-1234 \
  --region us-east-1
```

**KMS key policy must allow Rekognition:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "rekognition.amazonaws.com" },
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "*"
    }
  ]
}
```

### IAM role for Rekognition (general purpose)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:CreateCollection",
        "rekognition:DescribeCollection",
        "rekognition:DeleteCollection",
        "rekognition:IndexFaces",
        "rekognition:SearchFaces",
        "rekognition:SearchFacesByImage",
        "rekognition:ListFaces",
        "rekognition:DeleteFaces",
        "rekognition:DetectLabels",
        "rekognition:DetectText",
        "rekognition:DetectModerationLabels",
        "rekognition:DetectProtectiveEquipment",
        "rekognition:RecognizeCelebrities"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-face-bucket/*"
    }
  ]
}
```

## Step 12 — SNS notifications for async jobs

Async operations (Start*) support SNS notification on completion.

**Create an SNS topic and allow Rekognition:**

```bash
aws sns create-topic --name rekognition-complete --region us-east-1
```

**SNS topic access policy (allow Rekognition to publish):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "rekognition.amazonaws.com" },
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:123456789012:rekognition-complete"
    }
  ]
}
```

**IAM role for SNS notification:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "rekognition.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permissions (for the notification role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:us-east-1:123456789012:rekognition-complete"
    }
  ]
}
```

## Step 13 — Cost and rate limiting

### Cost per operation

| Operation | Pricing (us-east-1) | Notes |
|---|---|---|
| IndexFaces | ~$0.001 per face | First 1M faces/month tiered |
| SearchFacesByImage | ~$0.001 per image | First 1M searches/month tiered |
| DetectLabels | ~$0.001 per image | First 1M images/month tiered |
| DetectModerationLabels | ~$0.001 per image | First 1M images/month tiered |
| DetectText | ~$0.001 per image | First 1M images/month tiered |
| RecognizeCelebrities | ~$0.001 per image | First 1M images/month tiered |
| Stream processor | ~$0.107 per minute | Billed while processor is running |
| Custom labels (training) | ~$1.00 per hour | Billed while training |
| Custom labels (inference) | ~$4.00 per hour per inference unit | Billed while model is RUNNING |

**Custom labels cost trap:** the model charges per hour while RUNNING,
not per inference. Stop the model when not in use:

```bash
aws rekognition stop-project-version \
  --project-version-arn "<arn>" \
  --region us-east-1
```

### Rate limiting (TPS)

Rekognition has TPS limits per account per region. Default limits vary
by operation.

```bash
# Check current service quotas
aws service-quotas get-service-quota \
  --service-code rekognition \
  --quota-code L-XXXX \
  --region us-east-1
```

**Throughput throttling:** when the TPS limit is exceeded, Rekognition
returns `ThrottlingException`. Implement exponential backoff in the
client.

**Index and search share quotas:** IndexFaces and SearchFacesByImage
share the same TPS quota. Heavy indexing can throttle search
performance. Schedule indexing during off-peak hours.

### Collection size limits

| Metric | Limit | Action when approaching |
|---|---|---|
| Faces per collection | 50,000,000 | Partition into multiple collections |
| Collections per region | Service quota | Request quota increase |
| Image size | 5 MB | Compress before upload |
| Face image minimum | 80x80 pixels | Upscale or reject small images |

## NEVER do these things

1. **NEVER create a collection without KMS encryption if compliance
   requires it.** KMS encryption CANNOT be added after creation. If
   encryption is needed, specify `--kms-key-id` at `create-collection`
   time. Re-creating an encrypted collection means re-indexing all
   faces.

2. **NEVER use a similarity threshold below 80% for production face
   matching.** Below 80%, false positive rates increase significantly,
   especially as collection size grows. Use 85%+ for collections over
   100k faces.

3. **NEVER assume the stream processor scales itself.** Throughput is
   determined by the input Kinesis stream's shard count. Scale shards to
   scale throughput. A single shard limits the processor to one
   concurrent consumer.

4. **NEVER leave a custom labels model running when not in use.**
   Custom labels models incur hourly charges while running. Always
   `stop-project-version` when inference is not needed.

5. **NEVER index faces without `--external-image-id`.** Without it,
   FaceIds are opaque UUIDs with no human-readable mapping. Set
   ExternalImageId to an employee ID, user ID, or other meaningful
   identifier.

6. **NEVER assume SNS notifications work with synchronous operations.**
   SNS notifications only work with async (Start*) operations.
   Synchronous operations (Detect*, Search*) return results directly.

7. **NEVER forget that index and search share TPS quotas.** Heavy
   indexing can throttle search performance. Schedule bulk indexing
   during off-peak hours.

8. **NEVER create a stream processor without the IAM role having all
   three permissions.** The role needs `kinesis:GetRecords` on the input
   stream, `kinesis:PutRecord` on the output stream, AND
   `rekognition:SearchFaces` on the collection. Missing any of the three
   causes silent failures.

9. **NEVER assume collection search latency is constant as faces grow.**
   Search latency degrades as face count increases. At 1M+ faces,
   consider partitioning into multiple collections by region or
   category.

10. **NEVER use Rekognition without exponential backoff on
    ThrottlingException.** The TPS limit is per account per region.
    Without backoff, batch operations will fail.

## Output format

```text
REKOGNITION: <collection-id> (<collection-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Collection: <collection-id> — created | existing
  [✓|✗] KMS encryption: enabled (<key-id>) | disabled
  [✓|✗] Face indexing: <count> faces indexed, ExternalImageId=<yes|no>
  [✓|✗] Face search threshold: <threshold>% (80%+ recommended)
  [✓|✗] Collection size: <count>/<limit> faces (<percentage>% capacity)
  [✓|✗] Stream processor: <name> — <status> (input shards: <count>)
  [✓|✗] Input Kinesis stream: <stream-name> (<shard-count> shards)
  [✓|✗] Output Kinesis stream: <stream-name> (<shard-count> shards)
  [✓|✗] Stream processor IAM role: <role-arn>
  [✓|✗] Celebrity recognition: <enabled|disabled>
  [✓|✗] Content moderation: <enabled|disabled> (min confidence: <value>%)
  [✓|✗] Text detection: <enabled|disabled>
  [✓|✗] Label detection: <enabled|disabled> (max labels: <count>)
  [✓|✗] PPE detection: <enabled|disabled>
  [✓|✗] Custom labels: <project-name>/<version> — <status>
  [✓|✗] SNS topic (async): <topic-arn>
  [✓|✗] IAM role ( Rekognition): <role-arn>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws rekognition describe-collection --collection-id <collection-id> --region <region>
  aws rekognition list-faces --collection-id <collection-id> --region <region>
  aws rekognition describe-stream-processor --name <processor-name> --region <region>
```

### Worked example — face collection with stream processor

```text
REKOGNITION: employee-faces (arn:aws:rekognition:us-east-1:123456789012:collection/employee-faces)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Collection: employee-faces — created
  [✓] KMS encryption: enabled (arn:aws:kms:us-east-1:123456789012:key/abcd-1234)
  [✓] Face indexing: 50000 faces indexed, ExternalImageId=yes
  [✓] Face search threshold: 85% (80%+ recommended)
  [✓] Collection size: 50000/50000000 faces (0.1% capacity)
  [✓] Stream processor: camera-feed-processor — RUNNING (input shards: 4)
  [✓] Input Kinesis stream: rekognition-input (4 shards)
  [✓] Output Kinesis stream: rekognition-output (2 shards)
  [✓] Stream processor IAM role: arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole
  [✓] Celebrity recognition: disabled
  [✓] Content moderation: enabled (min confidence: 60%)
  [✓] Text detection: disabled
  [✓] Label detection: disabled
  [✓] PPE detection: disabled
  [✓] Custom labels: N/A
  [✓] SNS topic (async): arn:aws:sns:us-east-1:123456789012:rekognition-complete
  [✓] IAM role (Rekognition): arn:aws:iam::123456789012:role/RekognitionRole
  [✓] Tags: Environment=production, UseCase=employee-access
VERIFICATION_COMMANDS:
  aws rekognition describe-collection --collection-id employee-faces --region us-east-1
  aws rekognition list-faces --collection-id employee-faces --region us-east-1
  aws rekognition describe-stream-processor --name camera-feed-processor --region us-east-1
```

## Error handling

### Collection already exists
- Use `describe-collection` to verify the existing collection. If the
  collection ID is in use, choose a different ID or delete the existing
  one with `delete-collection` (this removes all faces).

### KMS access denied
- The KMS key policy must allow `rekognition.amazonaws.com` to call
  `kms:Decrypt` and `kms:GenerateDataKey`. Verify the key policy
  includes the Rekognition service principal.

### Stream processor fails to start
- Verify the IAM role has all three permissions: `kinesis:GetRecords`
  on input, `kinesis:PutRecord` on output, `rekognition:SearchFaces`
  on the collection. Check that both Kinesis streams exist and are
  ACTIVE.

### ThrottlingException
- The TPS limit is exceeded. Implement exponential backoff. If indexing
  is causing search throttling, schedule indexing during off-peak hours
  or request a quota increase.

### Low face match quality
- Increase the similarity threshold to 85-90%. Verify image quality
  (lighting, resolution, face angle). If the collection has over 1M
  faces, consider partitioning into multiple collections.

### Custom labels model too expensive
- The model charges hourly while running. Stop the model
  (`stop-project-version`) when not in use. Schedule inference windows
  or use EventBridge to auto-start/stop.

## Domain

AWS CloudOps / Amazon Rekognition Face Collection & Detection Pipeline
Provisioning.

## AWS documentation

- **Rekognition Developer Guide** — https://docs.aws.amazon.com/rekognition/latest/dg/what-is.html
- **Collections** — https://docs.aws.amazon.com/rekognition/latest/dg/collections.html
- **Searching faces** — https://docs.aws.amazon.com/rekognition/latest/dg/search-faces.html
- **Stream processor** — https://docs.aws.amazon.com/rekognition/latest/dg/streaming-video.html
- **Content moderation** — https://docs.aws.amazon.com/rekognition/latest/dg/moderation.html
- **Celebrity recognition** — https://docs.aws.amazon.com/rekognition/latest/dg/celebrities.html
- **Custom labels** — https://docs.aws.amazon.com/rekognition/latest/customlabels-dg/cu-what-is-custom-labels.html
- **Pricing** — https://aws.amazon.com/rekognition/pricing/
- **KMS encryption** — https://docs.aws.amazon.com/rekognition/latest/dg/security-encryption-at-rest.html
