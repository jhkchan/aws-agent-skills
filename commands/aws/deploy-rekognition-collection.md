---
description: Provision an Amazon Rekognition face collection and detection pipeline with production-grade defaults (KMS encryption at creation, face indexing with ExternalImageId, similarity threshold 80%+, stream processor with Kinesis shard-level parallelism, content moderation, label/text/PPE detection, custom labels lifecycle, SNS async notification). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create rekognition collection"
  - "deploy rekognition collection"
  - "index faces"
  - "search faces by image"
  - "face search similarity threshold"
  - "rekognition stream processor"
  - "celebrity recognition"
  - "content moderation"
  - "text in image detection"
  - "label detection"
  - "ppe detection"
  - "custom labels model training"
  - "rekognition kms encryption"
  - "face collection"
routes_to: rekognition-collection-deployer
---

# /aws:deploy-rekognition-collection

Activate the `rekognition-collection-deployer` skill and provision an
Amazon Rekognition face collection and detection pipeline with
production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Collection creation and size limits (50M faces max)
2. Face indexing with FaceId generation and ExternalImageId
3. Face search by image and by FaceId
4. Similarity threshold tuning (80%+ for production)
5. Stream processor for video analysis (Kinesis shard-level parallelism)
6. Celebrity recognition (built-in index)
7. Content moderation (unsafe content detection)
8. Text in image and label detection
9. PPE detection (safety compliance)
10. Custom labels model training and deployment
11. KMS encryption and IAM roles
12. SNS notifications for async jobs
13. Cost and rate limiting (TPS, per-image pricing)

## When to use

- You need to create a Rekognition face collection.
- You need to index faces and search by image or FaceId.
- You need a stream processor for real-time video face matching.
- You need content moderation, label detection, or text detection.
- You need PPE detection for safety compliance.
- You need to train and deploy custom labels models.
- You need celebrity recognition.
- You need KMS encryption for compliance (GDPR, HIPAA).

## When NOT to use

- **Amazon Textract** — for document text extraction (different service).
- **Amazon Transcribe** — for speech-to-text (different service).
- **Amazon Comprehend** — for NLP/text analysis (different service).
- **Auditing existing Rekognition collections** — use Rekognition audit skills.

## How to invoke

### Slash command

```
/aws:deploy-rekognition-collection
```

Then provide: collection ID, KMS key ARN (if encryption needed),
face count estimate, similarity threshold, stream processor name (if
video analysis), Kinesis stream names and shard counts, SNS topic
ARN (if async jobs), IAM role ARNs, tags.

### Natural language

Any of these routes to the same skill:

- "create a rekognition collection with kms encryption"
- "index faces into my collection"
- "search faces by image with 85 percent threshold"
- "create a stream processor for video face matching"
- "set up content moderation with sns notification"
- "train a custom labels model for defect detection"

### CLI routing

```bash
node cli/bin/cli.js route "create a rekognition collection"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Rekognition
collections or detection pipelines. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-rekognition-collection

     Create a Rekognition collection employee-faces in us-east-1
     with KMS encryption key arn:aws:kms:us-east-1:...:key/abcd.
     Index 50000 faces. Threshold 85%. Create a stream processor
     reading from rekognition-input (4 shards).

Skill:
  REKOGNITION: employee-faces
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Collection: employee-faces — created
    [✓] KMS encryption: enabled (arn:aws:kms:...:key/abcd)
    [✓] Face indexing: 50000 faces, ExternalImageId=yes
    [✓] Face search threshold: 85%
    [✓] Stream processor: camera-feed-processor (4 input shards)
  VERIFICATION_COMMANDS:
    aws rekognition describe-collection --collection-id employee-faces --region us-east-1
    aws rekognition describe-stream-processor --name camera-feed-processor --region us-east-1
```

## References

- Skill definition: `skills/rekognition-collection-deployer/SKILL.md`
- Face search and threshold guide: `skills/rekognition-collection-deployer/references/face-search-and-threshold.md`
- Stream processor and async guide: `skills/rekognition-collection-deployer/references/stream-processor-and-async.md`
- Eval suite: `skills/rekognition-collection-deployer/evals/evals.json`
