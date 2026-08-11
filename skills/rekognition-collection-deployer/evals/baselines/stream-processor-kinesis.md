# Baseline (no-skill) — stream-processor-kinesis

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the shard-level
> parallelism requirement (throughput is determined by Kinesis shard
> count), the triple IAM permission requirement (Kinesis read + Kinesis
> write + Rekognition search), and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create a stream processor:

```bash
aws rekognition create-stream-processor \
  --name camera-feed-processor \
  --input '{"KinesisStream":{"Arn":"..."}}' \
  --output '{"KinesisStream":{"Arn":"..."}}' \
  --role-arn "arn:aws:iam::123456789012:role/RekognitionStreamProcessorRole"
```

Then start it.
