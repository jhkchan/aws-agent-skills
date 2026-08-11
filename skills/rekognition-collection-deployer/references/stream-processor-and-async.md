# Stream Processor and Async Jobs — Rekognition Collection Deployer

Deep reference on stream processor configuration (Kinesis integration,
shard-level parallelism, IAM roles), async job patterns (SNS
notification, JobId retrieval), and cost optimization for video
analysis. Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## Stream processor architecture

### Data flow

```text
Camera feed
  → Frame extractor (Lambda / custom)
  → Kinesis data stream (input)       [shard count = parallelism]
  → Rekognition stream processor
    → SearchFacesByImage against collection
    → Match results
  → Kinesis data stream (output)      [shard count = output capacity]
  → Consumer (Lambda / dashboard / alerting)
```

Each record in the input Kinesis stream is a base64-encoded JPEG image
frame. The stream processor reads frames, searches them against the
collection, and writes match records to the output stream.

### Input stream configuration

```bash
# Create the input Kinesis stream with 4 shards
aws kinesis create-stream \
  --stream-name rekognition-input \
  --shard-count 4 \
  --region us-east-1

# Wait for ACTIVE
aws kinesis wait stream-exists --stream-name rekognition-input --region us-east-1
```

**Shard count determines parallelism.** Each shard provides ~1 MB/sec
ingest and 1 concurrent consumer. For 4 cameras at 2 fps, 4 shards is
typical.

### Output stream configuration

```bash
# Create the output Kinesis stream with 2 shards
aws kinesis create-stream \
  --stream-name rekognition-output \
  --shard-count 2 \
  --region us-east-1
```

**Output shards should be fewer than input shards** (match results are
smaller than image frames). Size output shards based on expected match
rate.

### Stream processor creation

```bash
aws rekognition create-stream-processor \
  --name "camera-feed-processor" \
  --input '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-input"}}' \
  --output '{"KinesisStream":{"Arn":"arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-output"}}' \
  --role-arn "arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole" \
  --settings '{"FaceSearch":{"CollectionId":"employee-faces","FaceMatchThreshold":85.0}}' \
  --region us-east-1
```

### Starting and stopping

```bash
# Start
aws rekognition start-stream-processor \
  --name "camera-feed-processor" \
  --start-selector '{"KVSStreamSelector":{"StartTimestamp":'"$(date +%s)"'}}' \
  --stop-selector '{"MaxDurationInSeconds":3600}' \
  --region us-east-1

# Stop
aws rekognition stop-stream-processor \
  --name "camera-feed-processor" \
  --region us-east-1

# Check status
aws rekognition describe-stream-processor \
  --name "camera-feed-processor" \
  --region us-east-1
```

## Stream processor IAM role

The IAM role MUST have all three permissions. Missing any one causes
silent failures or processing errors.

### Trust policy

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

### Permissions policy (the triple permission)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadInputStream",
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
      "Sid": "WriteOutputStream",
      "Effect": "Allow",
      "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/rekognition-output"
    },
    {
      "Sid": "SearchFacesInCollection",
      "Effect": "Allow",
      "Action": ["rekognition:SearchFaces", "rekognition:SearchFacesByImage"],
      "Resource": "arn:aws:rekognition:us-east-1:123456789012:collection/employee-faces"
    }
  ]
}
```

## Async job patterns

### Async operations that support SNS

| Operation | Start API | Get API |
|---|---|---|
| Face search in video | StartFaceSearch | GetFaceSearch |
| Label detection in video | StartLabelDetection | GetLabelDetection |
| Content moderation in video | StartContentModeration | GetContentModeration |
| Text detection in video | StartTextDetection | GetTextDetection |
| Face detection in video | StartFaceDetection | GetFaceDetection |
| Person tracking in video | StartPersonTracking | GetPersonTracking |
| Segment detection in video | StartSegmentDetection | GetSegmentDetection |
| Media analysis | StartMediaAnalysisJob | GetMediaAnalysisJob |

### SNS notification setup

```bash
# Create SNS topic
TOPIC_ARN=$(aws sns create-topic \
  --name rekognition-complete \
  --region us-east-1 \
  --query 'TopicArn' --output text)

# Allow Rekognition to publish
aws sns set-topic-attributes \
  --topic-arn "$TOPIC_ARN" \
  --attribute-name Policy \
  --attribute-value '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"rekognition.amazonaws.com"},"Action":"sns:Publish","Resource":"'$TOPIC_ARN'"}]}'
```

### Starting an async job with SNS

```bash
JOB_ID=$(aws rekognition start-label-detection \
  --video '{"S3Object":{"Bucket":"my-video-bucket","Name":"video.mp4"}}' \
  --notification-channel '{"SNSTopicArn":"'$TOPIC_ARN'","RoleArn":"arn:aws:iam::123456789012:role/RekognitionSNSRole"}' \
  --min-confidence 75 \
  --region us-east-1 \
  --query 'JobId' --output text)
```

### Retrieving async results

```bash
aws rekognition get-label-detection \
  --job-id "$JOB_ID" \
  --sort-by TIMESTAMP \
  --region us-east-1
```

## Cost optimization

### Stream processor cost

The stream processor bills per minute while RUNNING (~$0.107/min in
us-east-1). Stop it when video feeds are offline:

```bash
aws rekognition stop-stream-processor \
  --name "camera-feed-processor" \
  --region us-east-1
```

Use EventBridge to auto-start/stop based on schedule:

```bash
# Auto-stop at 6pm
aws events put-rule \
  --name "stop-processor-evening" \
  --schedule-expression "cron(0 18 * * ? *)" \
  --region us-east-1
```

### Custom labels cost

Custom labels models bill per hour per inference unit (~$4.00/hr per
inference unit). Stop the model when not needed:

```bash
aws rekognition stop-project-version \
  --project-version-arn "<arn>" \
  --region us-east-1
```

### Batch vs real-time cost

| Pattern | Cost | Latency |
|---|---|---|
| Sync Detect* (per image) | ~$0.001/image | Real-time |
| Async Start* (per video) | ~$0.001/sec of video | Minutes |
| Stream processor (continuous) | ~$0.107/min | Real-time |
| Custom labels inference | ~$4.00/hr per unit | Real-time |

**Rule:** use sync for low-volume image analysis, async for batch video
processing, stream processor for continuous live video feeds, and
custom labels only when the model is actively needed.

## Common pitfalls

### Pitfall 1: Stream processor not processing

**Cause:** IAM role missing one of the three permissions, or Kinesis
streams not ACTIVE.

**Fix:** verify the IAM role policy includes Kinesis read on input,
Kinesis write on output, AND Rekognition search on collection. Verify
both streams are ACTIVE.

### Pitfall 2: Output stream throttled

**Cause:** output Kinesis stream has too few shards for the match rate.

**Fix:** increase output stream shard count. Monitor
`WriteProvisionedThroughputExceeded` CloudWatch metric.

### Pitfall 3: SNS notification not received

**Cause:** SNS topic access policy does not allow Rekognition to
publish, or the IAM role for notification lacks `sns:Publish`.

**Fix:** verify the topic policy includes
`"Principal":{"Service":"rekognition.amazonaws.com"}` and the
notification role has `sns:Publish` permission.

### Pitfall 4: Custom labels model running up costs

**Cause:** model left in RUNNING state after inference is complete.

**Fix:** always `stop-project-version` when done. Use EventBridge or
Lambda to auto-stop on a schedule.
