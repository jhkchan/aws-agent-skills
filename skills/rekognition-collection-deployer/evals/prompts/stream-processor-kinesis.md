# Eval: stream-processor-kinesis

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — stream processor reading from 4-shard Kinesis input, writing to 2-shard output, face match threshold 85%, IAM role with triple permission

## Prompt

Create a Rekognition stream processor "camera-feed-processor" in
us-east-1. Input stream: rekognition-input (4 shards). Output
stream: rekognition-output (2 shards). Collection: employee-faces.
Face match threshold: 85%. IAM role:
arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole.
Tags: Environment=production, Pipeline=video-access.
