# End-to-End Example: Rekognition Collection Deployment

A walkthrough showing how to use the `rekognition-collection-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Rekognition face collection with KMS encryption
for an employee access control system, plus a stream processor for
real-time camera feed face matching. The deployment needs:

- Collection: employee-faces (KMS encrypted)
- Face indexing: 50,000 employees with ExternalImageId
- Face search threshold: 85%
- Stream processor: camera-feed-processor (4 input shards, 2 output shards)
- SNS topic: rekognition-complete (async job notifications)
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-rekognition-collection
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Rekognition collection employee-faces in us-east-1
      with KMS encryption. Index 50000 faces with ExternalImageId.
      Set face search threshold to 85%. Create a stream processor
      reading from rekognition-input (4 shards) and writing to
      rekognition-output (2 shards)."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a rekognition collection"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
REKOGNITION: employee-faces (arn:aws:rekognition:us-east-1:123456789012:collection/employee-faces)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Collection: employee-faces — created
  [✓] KMS encryption: enabled (arn:aws:kms:us-east-1:123456789012:key/abcd-1234)
  [✓] Face indexing: 50000 faces, ExternalImageId=yes
  [✓] Face search threshold: 85% (80%+ recommended)
  [✓] Collection size: 50000/50000000 faces (0.1% capacity)
  [✓] Stream processor: camera-feed-processor — RUNNING (input shards: 4)
  [✓] Input Kinesis stream: rekognition-input (4 shards)
  [✓] Output Kinesis stream: rekognition-output (2 shards)
  [✓] Stream processor IAM role: arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole
  [✓] SNS topic (async): arn:aws:sns:us-east-1:123456789012:rekognition-complete
  [✓] Tags: Environment=production, UseCase=employee-access
VERIFICATION_COMMANDS:
  aws rekognition describe-collection --collection-id employee-faces --region us-east-1
  aws rekognition list-faces --collection-id employee-faces --region us-east-1
  aws rekognition describe-stream-processor --name camera-feed-processor --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the collection with KMS encryption (CANNOT be added later)
aws rekognition create-collection \
  --collection-id "employee-faces" \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd-1234 \
  --region us-east-1

# Step 2: Index faces with ExternalImageId
aws rekognition index-faces \
  --collection-id "employee-faces" \
  --image '{"S3Object":{"Bucket":"my-face-bucket","Name":"employee-001.jpg"}}' \
  --external-image-id "employee-001" \
  --max-faces 1 \
  --quality-filter "AUTO" \
  --region us-east-1

# Step 3: Create the stream processor
aws rekognition create-stream-processor \
  --name "camera-feed-processor" \
  --input '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-input"}}' \
  --output '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-output"}}' \
  --role-arn "arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole" \
  --settings '{"FaceSearch":{"CollectionId":"employee-faces","FaceMatchThreshold":85.0}}' \
  --region us-east-1

# Step 4: Start the stream processor
aws rekognition start-stream-processor \
  --name "camera-feed-processor" \
  --start-selector '{"KVSStreamSelector":{"StartTimestamp":'"$(date +%s)"'}}' \
  --stop-selector '{"MaxDurationInSeconds":3600}' \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Collection status — verify KMS encryption
aws rekognition describe-collection \
  --collection-id employee-faces \
  --region us-east-1

# Stream processor status
aws rekognition describe-stream-processor \
  --name camera-feed-processor \
  --region us-east-1

# Verify face search works
aws rekognition search-faces-by-image \
  --collection-id "employee-faces" \
  --image '{"S3Object":{"Bucket":"my-face-bucket","Name":"test-query.jpg"}}' \
  --face-match-threshold 85 \
  --max-faces 5 \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| KMS encryption | Created without KMS; tries to add later | KMS at creation time | KMS CANNOT be added after collection creation |
| ExternalImageId | Not set; FaceIds are opaque UUIDs | ExternalImageId for each face | Traceability from FaceId to employee ID |
| Similarity threshold | Default 80% or lower | 85% for 50k+ faces | False positive rate rises with collection size |
| Stream processor IAM | Missing one permission | All three permissions verified | Silent failure if any permission is missing |
| Shard-level parallelism | Not considered | Input shard count determines throughput | More shards = more concurrent face searches |
| Custom labels cost | Model left running | Stop when not in use | Hourly charges accrue while RUNNING |

---

## Related artifacts

- **Skill definition:** `skills/rekognition-collection-deployer/SKILL.md`
- **Face search and threshold guide:** `skills/rekognition-collection-deployer/references/face-search-and-threshold.md`
- **Stream processor and async guide:** `skills/rekognition-collection-deployer/references/stream-processor-and-async.md`
- **Slash command:** `commands/aws/deploy-rekognition-collection.md`
- **Eval suite:** `skills/rekognition-collection-deployer/evals/evals.json`
- **Legacy test cases:** `skills/rekognition-collection-deployer/eval/test-cases.yaml`
