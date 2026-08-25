---
name: rekognition-collection-deployer
description: 'Provisions Amazon Rekognition face collections and detection pipelines: collection creation with KMS encryption (must be set at create time), face indexing (index-faces, FaceId, ExternalImageId), face search by image and by FaceId with similarity threshold tuning (80%+ for production), stream processor for video analysis (Kinesis shard-level parallelism), celebrity recognition, content moderation, text in image, label detection, PPE detection, custom labels model training and deployment, SNS notification for async jobs, KMS encryption, IAM roles, cost per image/video, rate limiting (TPS), and collection size limits. Emits a READY_TO_DEPLOY checklist. Triggers: create rekognition collection, index faces, search faces by image, face search similarity threshold, rekognition stream processor, celebrity recognition, content moderation, ppe detection, custom labels model training, rekognition kms encryption.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with rekognition access. Works with Terraform aws_rekognition_collection / aws_rekognition_stream_processor resources and CloudFormation AWS::Rekognition::Collection templates.'
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
  tags: aws, rekognition, face-collection, cloudops, deploy, ai-ml, provisioning, stream-processor, content-moderation, celebrity-recognition, custom-labels
  dependencies: aws-orchestrator
  keywords: aws, rekognition, face collection, face search, cloudops, deploy, provisioning, stream processor, celebrity recognition, content moderation, label detection, custom labels, kms encryption
  when_to_use: Invoke when the user wants to create a Rekognition face collection, index faces, search faces by image or FaceId, set up a stream processor for video analysis, detect labels or text, run content moderation, detect PPE, train and deploy custom labels models, configure celebrity recognition, or integrate Rekognition with Kinesis, SNS, and KMS. Do NOT invoke for Amazon Textract, Amazon Transcribe, or Amazon Comprehend — those are separate services.
---

# Rekognition Collection Deployer

An AWS CloudOps agent skill that provisions Amazon Rekognition face
collections and detection pipelines with correct defaults. The skill
walks the operator through collection creation, face indexing, face
search with similarity threshold tuning, stream processor configuration,
content moderation, label and text detection, PPE detection, celebrity
recognition, custom labels model training, KMS encryption, IAM roles,
SNS notifications, cost and rate limit considerations, and collection
size limits — captures detection requirements, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create Rekognition collection, index faces, search faces by image, face
search similarity threshold, Rekognition stream processor, celebrity
recognition, content moderation, text in image detection, label
detection, PPE detection, custom labels model training, Rekognition KMS
encryption.

## STRICT output contract

When this skill is invoked with a Rekognition-provisioning request,
the agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`REKOGNITION:`, `VERDICT:`, `CHECKLIST:`, and
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
| Step 6 — Celebrity recognition and moderation | Detection features |
| Step 7 — Label, text, and PPE detection | Scene/safety analysis |
| Step 8 — Custom labels model lifecycle | Custom model training |
| Step 9 — KMS encryption and IAM roles | Security |
| Step 10 — SNS, cost, and rate limiting | Async, economics, TPS |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/face-search-and-threshold.md | Face search + threshold detail |
| references/stream-processor-and-async.md | Stream processor + async detail |

## Mindset

**One-line takeaway:** A Rekognition collection is a managed face
vector store. You create it, index faces into it (each face gets a
FaceId), and search by image or FaceId. The similarity threshold
determines match strictness — 80%+ is production-grade. For video
analysis, the stream processor reads from a Kinesis stream and writes
face matches to another stream with shard-level parallelism.

Three misconceptions dominate Rekognition misdesign at provisioning
time:

- **"The default similarity threshold is fine."** The API default is
  80%, but operators pass lower thresholds (50-60%) to get more
  matches. This produces false positives at scale. For production face
  matching, 80%+ is the minimum; below 80%, false positive rates rise
  significantly as collection size grows.

- **"Collections scale infinitely."** A single collection supports up
  to 50 million faces, but search latency degrades as face count grows.
  At 1M+ faces, consider partitioning by region or category into
  multiple collections. Index-faces and search-faces-by-image also
  share the same TPS quota.

- **"The stream processor handles scaling."** The stream processor
  reads from Kinesis shards. Throughput is bounded by shard count.
  Shard-level parallelism is the scaling lever — more shards = more
  parallel face searches. A single shard limits the processor to one
  concurrent consumer.

## Configuration dependency graph (novel heuristic)

Rekognition configurations are NOT independent. The collection must
exist before faces are indexed. Faces must be indexed before they can
be searched. The stream processor needs BOTH a Kinesis input stream
and a Kinesis output stream. KMS encryption must be configured at
collection creation time (not retroactively). Custom labels models
must be trained before they can be started.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Collection | KMS key (if encrypted); IAM `rekognition:CreateCollection` | KMS encryption CANNOT be added after creation | face indexing, face search |
| Face indexing | Collection exists; image in S3 or bytes | FaceId is server-generated; ExternalImageId recommended for traceability | face search by FaceId |
| Face search (by image) | Collection has indexed faces; IAM `rekognition:SearchFacesByImage` | similarity threshold below 80% produces false positives at scale | face matching results |
| Stream processor | Kinesis input stream; Kinesis output stream; IAM role with all three permissions | shard count determines parallelism; missing any IAM permission causes silent failure | real-time video face detection |
| Content moderation | IAM `rekognition:DetectModerationLabels` | works without a collection | unsafe content flags |
| Custom labels model | S3 training data; IAM role; dataset labeled | model MUST be started (start-project-version) after training; inference costs accrue hourly | custom label inference |
| KMS encryption | KMS key with proper key policy | CANNOT be added after creation — MUST be set at create time | encryption at rest |
| SNS notification | SNS topic; IAM role with `sns:Publish` | only async (Start*) operations support SNS | async job completion callbacks |

**The KMS-at-creation row is the one a baseline model misses.** KMS
encryption cannot be added to an existing collection. If encryption is
required (compliance, GDPR, HIPAA), the KMS key ID MUST be specified at
`create-collection` time. Re-creating an encrypted collection means
re-indexing all faces.

**Cross-dependency gotchas:**
- The stream processor needs a Kinesis data stream (not Kinesis Video
  Stream). Each record is a base64-encoded JPEG frame.
- Face indexing and search share the same TPS quota. Heavy indexing
  throttles search. Plan indexing during off-peak hours.
- Custom labels models incur hourly charges while running. Stop the
  model when not in use.
- SNS notifications only work with async (Start*) operations, not
  synchronous (Detect*, Search*) operations.

## Expert heuristic: similarity threshold 80%+ for face matching

A baseline model says "search faces with the default threshold." The
correct heuristic recognizes that threshold tuning is the single most
important quality lever in production face matching.

```text
Similarity threshold guide:
  99%+   → near-exact (identity verification, access control)
  90-99% → strict matching (badge systems, attendance)
  80-90% → production-grade (balanced; recommended default)
  60-80% → loose matching (human-in-the-loop review only)
  <60%   → NOT recommended (false positives dominate)

Collection size impact on accuracy:
  <10k faces      → 80% threshold is reliable
  10k-100k faces  → 80% recommended; consider 85% for tighter matching
  100k-1M faces   → 85%+ recommended; false positive rate rises
  1M-10M faces    → 90%+ recommended; consider collection partitioning
  10M+ faces      → MUST partition into multiple collections
```

**Key implication:** the threshold is not "set and forget." As the
collection grows, the threshold may need to increase to maintain the
same false-positive rate.

## Expert heuristic: stream processor shard-level parallelism

The stream processor reads from Kinesis shards. Each shard is processed
by one consumer. More shards = more parallel face searches = higher
throughput.

```text
Stream processor throughput scaling:
  Input Kinesis stream shard count:
    1 shard  → 1 concurrent face search
    4 shards → 4 concurrent face searches
    N shards → N concurrent face searches (linear scaling)

  Output Kinesis stream:
    Needs enough shards to absorb output rate
    If output is throttled, processor backs up

  Typical production setup:
    Input: 4-8 shards (camera feeds at 1-5 fps per camera)
    Output: 2-4 shards (match results, smaller payloads)
```

**Key implication:** the processor's throughput is NOT configurable via
the Rekognition API — it is determined entirely by the input Kinesis
stream's shard count.

## Expert heuristic: collection face count scaling

A baseline model says "one collection for everything." The correct
heuristic recognizes that search latency and false positive rates
degrade as face count grows. Partitioning strategy should be decided
BEFORE indexing begins.

```text
Collection size decision tree:
  <1M faces    → single collection is fine; threshold 80%+
  1M-10M faces → single collection works; increase threshold to 85-90%
  10M+ faces   → MUST partition by region/category; 90%+ threshold
  Multi-region → partition by region for data residency + latency
```

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS region supports Rekognition | Not all regions support all features | Check service availability |
| KMS key (if encryption required) | KMS must be set at creation | `aws kms describe-key --key-id <key-id>` |
| IAM role for stream processor | Needs Kinesis read + write + Rekognition search | Verify role permissions |
| Kinesis input/output streams | Stream processor reads/writes Kinesis | `aws kinesis describe-stream` |
| S3 bucket for images/video | Index and async operations read from S3 | `aws s3 ls s3://<bucket>` |
| SNS topic (if async notifications) | Async jobs send completion to SNS | `aws sns get-topic-attributes` |
| Collection size estimate | Affects threshold and partitioning decisions | Estimate face count |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Collection creation and size limits

A Rekognition collection is a managed vector index of face feature
vectors. Each collection can hold up to 50 million faces.

```bash
# Create a collection (no encryption)
aws rekognition create-collection \
  --collection-id "employee-faces" --region us-east-1

# Create a collection WITH KMS encryption (MUST be set at creation)
aws rekognition create-collection \
  --collection-id "employee-faces" \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd-1234 \
  --region us-east-1
```

**Critical:** KMS encryption CANNOT be added after creation.

| Limit | Value |
|---|---|
| Max faces per collection | 50,000,000 |
| Face image max size | 5 MB (JPEG/PNG) |
| Face image min size | 80x80 pixels |

## Step 2 — Face indexing (FaceId generation)

Indexing adds faces to the collection. Each indexed face gets a unique
server-generated FaceId.

```bash
aws rekognition index-faces \
  --collection-id "employee-faces" \
  --image '{"S3Object":{"Bucket":"my-face-bucket","Name":"emp-001.jpg"}}' \
  --external-image-id "employee-001" \
  --max-faces 1 \
  --quality-filter "AUTO" \
  --region us-east-1
```

**Key parameters:**
- `--external-image-id`: Maps FaceId to external identifier (employee
  ID). Recommended for traceability.
- `--max-faces`: Limits faces indexed per image. Set to 1 for
  single-person photos.
- `--quality-filter`: `AUTO` (recommended) filters low-quality faces.

**Common mistake:** indexing without `--external-image-id` — FaceIds
become opaque UUIDs with no human-readable mapping.

## Step 3 — Face search by image and by FaceId

**Search by image:**

```bash
aws rekognition search-faces-by-image \
  --collection-id "employee-faces" \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"query.jpg"}}' \
  --face-match-threshold 80 \
  --max-faces 5 --region us-east-1
```

**Search by FaceId (find duplicates):**

```bash
aws rekognition search-faces \
  --collection-id "employee-faces" \
  --face-id "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --face-match-threshold 80 \
  --max-faces 5 --region us-east-1
```

Response includes `FaceMatches` with `Similarity` (0-100) and
`ExternalImageId`.

## Step 4 — Similarity threshold tuning

| Threshold | Use case | False positive | False negative |
|---|---|---|---|
| 99%+ | Identity verification | Very low | High |
| 90-99% | Badge/access control | Low | Low |
| 80-90% | Production matching (recommended) | Moderate | Low |
| 60-80% | Human-in-the-loop review | High | Very low |
| <60% | NOT recommended | Very high | Near zero |

**Production recommendation:** start at 80%, monitor false positives,
increase to 85-90% if collection exceeds 100k faces.

## Step 5 — Stream processor for video analysis

The stream processor reads frames from a Kinesis data stream, searches
against a collection, and writes matches to a Kinesis output stream.

```bash
aws rekognition create-stream-processor \
  --name "camera-feed-processor" \
  --input '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-input"}}' \
  --output '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-output"}}' \
  --role-arn "arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole" \
  --settings '{"FaceSearch":{"CollectionId":"employee-faces","FaceMatchThreshold":85.0}}' \
  --region us-east-1
```

**Start and monitor:**

```bash
aws rekognition start-stream-processor \
  --name "camera-feed-processor" \
  --start-selector '{"KVSStreamSelector":{"StartTimestamp":'"$(date +%s)"'}}' \
  --stop-selector '{"MaxDurationInSeconds":3600}' \
  --region us-east-1

aws rekognition describe-stream-processor \
  --name "camera-feed-processor" --region us-east-1
```

**Stream processor IAM role MUST have all three permissions:**

| Permission | Resource |
|---|---|
| `kinesis:GetRecords`, `kinesis:GetShardIterator` | Input stream |
| `kinesis:PutRecord`, `kinesis:PutRecords` | Output stream |
| `rekognition:SearchFaces`, `rekognition:SearchFacesByImage` | Collection |

Missing any of the three causes silent failures.

## Step 6 — Celebrity recognition and moderation

**Celebrity recognition** (uses built-in celebrity index, no collection):

```bash
aws rekognition recognize-celebrities \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"event.jpg"}}' \
  --region us-east-1
```

**Content moderation (sync):**

```bash
aws rekognition detect-moderation-labels \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"user-upload.jpg"}}' \
  --min-confidence 60 --region us-east-1
```

**Content moderation (async video with SNS):**

```bash
JOB_ID=$(aws rekognition start-content-moderation \
  --video '{"S3Object":{"Bucket":"my-bucket","Name":"video.mp4"}}' \
  --min-confidence 60 \
  --notification-channel '{"SNSTopicArn":"arn:aws:sns:us-east-1:123456789012:rekognition-complete","RoleArn":"arn:aws:iam::123456789012:role/RekognitionSNSRole"}' \
  --region us-east-1 --query 'JobId' --output text)

aws rekognition get-content-moderation \
  --job-id "$JOB_ID" --region us-east-1
```

## Step 7 — Label, text, and PPE detection

**Label detection:**

```bash
aws rekognition detect-labels \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"photo.jpg"}}' \
  --max-labels 50 --min-confidence 75 --region us-east-1
```

**Text detection:**

```bash
aws rekognition detect-text \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"signage.jpg"}}' \
  --region us-east-1
```

**PPE detection:**

```bash
aws rekognition detect-protective-equipment \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"worksite.jpg"}}' \
  --required-equipment-types '["FACE_COVER","HAND_COVER","HEAD_COVER"]' \
  --region us-east-1
```

Response includes `Persons` with `BodyParts`, `EquipmentDetections`,
and `CoversBodyPart` boolean.

## Step 8 — Custom labels model lifecycle

Custom labels train a model on your specific images (industrial
defects, product logos, etc.).

```bash
# 1. Create project
aws rekognition create-project --project-name "industrial-defects" --region us-east-1

# 2. Create dataset and train model
aws rekognition create-project-version \
  --project-arn "<project-arn>" \
  --version-name "v1" \
  --output-config '{"S3Bucket":"my-bucket","S3KeyPrefix":"model-output/"}' \
  --training-data '{"Assets":[{"GroundTruthManifest":{"S3Object":{"Bucket":"my-bucket","Name":"training/manifest.json"}}}]}' \
  --testing-data '{"AutoCreate":true}' \
  --region us-east-1

# 3. Start model (inference) — charges hourly while RUNNING
aws rekognition start-project-version \
  --project-version-arn "<version-arn>" \
  --min-inference-units 1 --region us-east-1

# 4. STOP model when not in use (avoid idle charges)
aws rekognition stop-project-version \
  --project-version-arn "<version-arn>" --region us-east-1
```

**Critical:** custom labels models incur hourly charges while RUNNING
(~$4.00/hr per inference unit). Always stop when not in use.

## Step 9 — KMS encryption and IAM roles

KMS encryption for collections MUST be configured at creation time. The
KMS key policy must allow the Rekognition service principal:

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "rekognition.amazonaws.com" },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
  "Resource": "*"
}
```

**General Rekognition IAM role permissions:**

```json
{
  "Effect": "Allow",
  "Action": [
    "rekognition:CreateCollection", "rekognition:DescribeCollection",
    "rekognition:IndexFaces", "rekognition:SearchFaces",
    "rekognition:SearchFacesByImage", "rekognition:ListFaces",
    "rekognition:DetectLabels", "rekognition:DetectText",
    "rekognition:DetectModerationLabels",
    "rekognition:DetectProtectiveEquipment",
    "rekognition:RecognizeCelebrities"
  ],
  "Resource": "*"
}
```

## Step 10 — SNS notifications, cost, and rate limiting

### SNS for async jobs

Async operations (Start*) support SNS notification on completion. Sync
operations (Detect*, Search*) do NOT support SNS.

### Cost summary

| Operation | Pricing (us-east-1) | Notes |
|---|---|---|
| IndexFaces / SearchFacesByImage | ~$0.001 per face/image | First 1M tiered |
| DetectLabels / DetectModerationLabels | ~$0.001 per image | First 1M tiered |
| Stream processor | ~$0.107 per minute | Billed while RUNNING |
| Custom labels (training) | ~$1.00 per hour | Billed while training |
| Custom labels (inference) | ~$4.00 per hour per unit | Billed while model RUNNING |

**Custom labels cost trap:** the model charges per hour while RUNNING,
not per inference. Stop when not in use.

### Rate limiting (TPS)

Rekognition has per-account, per-region TPS limits. When exceeded,
returns `ThrottlingException`. Implement exponential backoff. Index and
search share the same TPS quota — heavy indexing throttles search.

## NEVER do these things

1. **NEVER create a collection without KMS encryption if compliance
   requires it.** KMS cannot be added after creation. Specify
   `--kms-key-id` at `create-collection` time.

2. **NEVER use a similarity threshold below 80% for production face
   matching.** False positive rates increase significantly below 80%,
   especially as collection size grows.

3. **NEVER assume the stream processor scales itself.** Throughput is
   determined by the input Kinesis stream's shard count. Scale shards
   to scale throughput.

4. **NEVER leave a custom labels model running when not in use.**
   Models incur hourly charges while running. Always
   `stop-project-version` when done.

5. **NEVER index faces without `--external-image-id`.** Without it,
   FaceIds are opaque UUIDs with no human-readable mapping.

6. **NEVER assume SNS notifications work with synchronous operations.**
   SNS only works with async (Start*) operations, not sync (Detect*,
   Search*).

7. **NEVER forget that index and search share TPS quotas.** Heavy
   indexing throttles search. Schedule bulk indexing off-peak.

8. **NEVER create a stream processor without verifying all three IAM
   permissions.** The role needs Kinesis read on input, Kinesis write
   on output, AND Rekognition search on the collection.

9. **NEVER assume search latency is constant as faces grow.** At 1M+
   faces, consider partitioning into multiple collections.

10. **NEVER use Rekognition without exponential backoff on
    ThrottlingException.** Without backoff, batch operations will fail.

## Output format

```text
REKOGNITION: <collection-id> (<collection-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Collection: <collection-id> — created | existing
  [✓|✗] KMS encryption: enabled (<key-id>) | disabled
  [✓|✗] Face indexing: <count> faces, ExternalImageId=<yes|no>
  [✓|✗] Face search threshold: <threshold>% (80%+ recommended)
  [✓|✗] Collection size: <count>/<limit> faces
  [✓|✗] Stream processor: <name> — <status> (input shards: <count>)
  [✓|✗] Input Kinesis stream: <stream-name> (<shard-count> shards)
  [✓|✗] Output Kinesis stream: <stream-name> (<shard-count> shards)
  [✓|✗] Stream processor IAM role: <role-arn>
  [✓|✗] Content moderation: <enabled|disabled> (min confidence: <value>%)
  [✓|✗] Label detection: <enabled|disabled> (max labels: <count>)
  [✓|✗] Text detection: <enabled|disabled>
  [✓|✗] PPE detection: <enabled|disabled>
  [✓|✗] Celebrity recognition: <enabled|disabled>
  [✓|✗] Custom labels: <project>/<version> — <status>
  [✓|✗] SNS topic (async): <topic-arn>
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
  [✓] Face indexing: 50000 faces, ExternalImageId=yes
  [✓] Face search threshold: 85% (80%+ recommended)
  [✓] Collection size: 50000/50000000 faces
  [✓] Stream processor: camera-feed-processor — RUNNING (input shards: 4)
  [✓] Input Kinesis stream: rekognition-input (4 shards)
  [✓] Output Kinesis stream: rekognition-output (2 shards)
  [✓] Stream processor IAM role: arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole
  [✓] Content moderation: enabled (min confidence: 60%)
  [✓] Label detection: disabled
  [✓] Text detection: disabled
  [✓] PPE detection: disabled
  [✓] Celebrity recognition: disabled
  [✓] Custom labels: N/A
  [✓] SNS topic (async): arn:aws:sns:us-east-1:123456789012:rekognition-complete
  [✓] Tags: Environment=production, UseCase=employee-access
VERIFICATION_COMMANDS:
  aws rekognition describe-collection --collection-id employee-faces --region us-east-1
  aws rekognition list-faces --collection-id employee-faces --region us-east-1
  aws rekognition describe-stream-processor --name camera-feed-processor --region us-east-1
```

## Error handling

### Collection already exists
- Use `describe-collection` to verify. Choose a different ID or delete
  the existing one with `delete-collection` (removes all faces).

### KMS access denied
- The KMS key policy must allow `rekognition.amazonaws.com` to call
  `kms:Decrypt` and `kms:GenerateDataKey`.

### Stream processor fails to start
- Verify the IAM role has all three permissions. Check both Kinesis
  streams are ACTIVE.

### ThrottlingException
- TPS limit exceeded. Implement exponential backoff. Schedule indexing
  off-peak or request quota increase.

### Low face match quality
- Increase threshold to 85-90%. Verify image quality. Partition if
  collection exceeds 1M faces.

### Custom labels model too expensive
- Stop model when not in use. Schedule inference windows via
  EventBridge auto-start/stop.

## Domain

AWS CloudOps / Amazon Rekognition Face Collection & Detection Pipeline
Provisioning.

## AWS documentation

- **Rekognition Developer Guide** — https://docs.aws.amazon.com/rekognition/latest/dg/what-is.html
- **Collections** — https://docs.aws.amazon.com/rekognition/latest/dg/collections.html
- **Searching faces** — https://docs.aws.amazon.com/rekognition/latest/dg/search-faces.html
- **Stream processor** — https://docs.aws.amazon.com/rekognition/latest/dg/streaming-video.html
- **Content moderation** — https://docs.aws.amazon.com/rekognition/latest/dg/moderation.html
- **Custom labels** — https://docs.aws.amazon.com/rekognition/latest/customlabels-dg/cu-what-is-custom-labels.html
- **Pricing** — https://aws.amazon.com/rekognition/pricing/
