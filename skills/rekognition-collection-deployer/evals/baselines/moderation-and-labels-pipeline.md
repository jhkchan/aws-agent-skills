# Baseline (no-skill) — moderation-and-labels-pipeline

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the SNS-only-for-async
> constraint (sync Detect* operations do not support SNS), the IAM role
> requirement for SNS notification, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Run content moderation:

```bash
aws rekognition detect-moderation-labels \
  --image '{"S3Object":{"Bucket":"my-video-bucket","Name":"image.jpg"}}'
```

Run label detection:

```bash
aws rekognition detect-labels \
  --image '{"S3Object":{"Bucket":"my-video-bucket","Name":"image.jpg"}}'
```
