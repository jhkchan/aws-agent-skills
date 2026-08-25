# ECR Replication Deployer — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Step 2 — verify replication is working (moved from SKILL.md)
**Verify replication is working:**

```bash
# Push an image to the source
docker push 111122223333.dkr.ecr.us-east-1.amazonaws.com/my-app:latest

# Check replication status
aws ecr describe-images \
  --repository-name my-app \
  --image-ids imageTag=latest \
  --region us-west-2 \
  --query 'imageDetails[0].imageTags' \
  --registry-id 111122223333
```

## Step 5 — checking replication status (moved from SKILL.md)
**Checking replication status:**

```bash
# Check image replication status via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECR \
  --metric-name ImageReplicationStatus \
  --dimensions Name=RepositoryName,Value=my-app \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

## Step 7 — CloudWatch alarm for replication failures (moved from SKILL.md)
```bash
# Create a CloudWatch alarm for replication failures
aws cloudwatch put-metric-alarm \
  --alarm-name "ECR-Replication-Failures" \
  --namespace AWS/ECR \
  --metric-name ImageReplicationStatus \
  --dimensions Name=RepositoryName,Value=my-app \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:111122223333:ecr-alerts"
```
