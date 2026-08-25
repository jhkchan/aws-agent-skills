# Diagnostic Commands — Rekognition Collection Deployer

Pre-flight discovery and post-deployment verification commands moved out of the SKILL.md body. Loaded on demand.


## Step 5 — Stream processor start and monitor commands

```bash
aws rekognition start-stream-processor \
  --name "camera-feed-processor" \
  --start-selector '{"KVSStreamSelector":{"StartTimestamp":'"$(date +%s)"'}}' \
  --stop-selector '{"MaxDurationInSeconds":3600}' \
  --region us-east-1

aws rekognition describe-stream-processor \
  --name "camera-feed-processor" --region us-east-1
```
