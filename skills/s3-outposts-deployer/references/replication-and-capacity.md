# Replication and Capacity Management — S3 Outposts Deployer

Deep reference on S3 on Outposts replication (one-way Outpost to cloud,
IAM roles, destination configuration), capacity management (finite
storage, monitoring, lifecycle strategies), and the differences from
cloud S3 lifecycle and archival. Loaded on demand by the skill.

## Replication architecture

### One-way replication: Outpost to cloud

S3 on Outposts supports replication FROM the Outpost bucket TO a cloud
S3 bucket. This is ONE-WAY only. You cannot replicate from cloud to
Outpost.

```text
Source (Outpost) ──── replication ────→ Destination (Cloud)
  outpost-bucket                          cloud-dr-bucket
  SSE-S3 only                             SSE-S3 or SSE-KMS
  STANDARD only                           STANDARD, IA, Glacier, etc.
```

Replication is the primary mechanism for:
- DR: replicate to cloud for off-Outpoint backup
- KMS compliance: replicate to cloud KMS-enabled bucket
- Archival: replicate to cloud then apply Glacier lifecycle rules

### Configuring replication

```bash
aws s3control put-bucket-replication \
  --account-id 123456789012 \
  --bucket "arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-0abc123def456/bucket/my-outpost-bucket" \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789012:role/S3OutpostsReplicationRole",
    "Rules": [{
      "Status": "Enabled",
      "Priority": 1,
      "Destination": {
        "Bucket": "arn:aws:s3:::cloud-dr-bucket"
      },
      "Filter": {},
      "DeleteMarkerReplication": { "Status": "Enabled" }
    }]
  }'
```

### Replication IAM role

The replication role needs read on the Outpost bucket and write on
the cloud destination:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3-outposts:GetObject",
        "s3-outposts:GetObjectVersion",
        "s3-outposts:GetBucketReplication"
      ],
      "Resource": "arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-xxx/bucket/my-outpost-bucket"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ReplicateObject",
        "s3:ReplicateDelete",
        "s3:ObjectOwnerOverrideToBucketOwner"
      ],
      "Resource": "arn:aws:s3:::cloud-dr-bucket/*"
    }
  ]
}
```

### Using cloud destination for archival

The cloud destination bucket can have lifecycle rules that transition
objects to Glacier or Deep Archive:

```bash
# Cloud bucket lifecycle (Glacier transition after 90 days)
aws s3api put-bucket-lifecycle-configuration \
  --bucket cloud-dr-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "Status": "Enabled",
      "Filter": {},
      "Transitions": [{ "Days": 90, "StorageClass": "GLACIER" }]
    }]
  }'
```

This is the recommended pattern: replicate from Outpost to cloud, then
archive on the cloud bucket. You cannot archive directly on the Outpost.

## Capacity management

### Finite storage

Outpost S3 storage is physically constrained by the Outpost rack
hardware. Unlike cloud S3 (virtually unlimited), Outpost storage has a
hard maximum. When the storage is full, new PUT requests fail with
`InsufficientStorageCapacity`.

### Monitoring capacity

```bash
# Get current bucket size
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3Outposts \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=my-outpost-bucket \
  --start-time 2026-08-11T00:00:00Z \
  --end-time 2026-08-11T01:00:00Z \
  --period 300 \
  --statistics Sum \
  --output text
```

### Capacity alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "outpost-s3-capacity-80pct" \
  --namespace AWS/S3Outposts \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=my-outpost-bucket \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 800000000000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:outpost-alerts"
```

### Capacity management strategies

1. **Lifecycle expiration:** delete old objects to free space
   ```json
   {"Rules":[{"Status":"Enabled","Filter":{},"Expiration":{"Days":90}}]}
   ```

2. **Replication + deletion:** replicate to cloud, then delete local
   copies on the Outpost after replication succeeds.

3. **Object lock with retention limits:** set maximum retention to
   prevent indefinite data accumulation.

4. **Versioning management:** expire old object versions to reclaim
   space from versioned objects.

## Lifecycle rules on Outpost

### What works

- **Expiration:** delete objects after N days
- **Noncurrent version expiration:** delete old versions after N days
- **Abort incomplete multipart uploads:** clean up incomplete uploads

### What does NOT work

- **Storage class transitions:** no Glacier, no IA (STANDARD only)
- **Intelligent tiering:** not available on Outpost
- **Object size-based rules:** limited compared to cloud S3

## Terraform examples

```hcl
# S3 on Outposts bucket
resource "aws_s3control_bucket" "main" {
  bucket = "my-outpost-bucket"

  outpost_id = "op-0abc123def456"

  versioning {
    enabled = true
  }
}

# Replication
resource "aws_s3control_bucket_replication" "main" {
  bucket = aws_s3control_bucket.main.arn

  replication_configuration {
    role = aws_iam_role.replication.arn

    rule {
      status   = "Enabled"
      priority = 1

      destination {
        bucket = "arn:aws:s3:::cloud-dr-bucket"
      }
    }
  }
}

# CloudWatch capacity alarm
resource "aws_cloudwatch_metric_alarm" "capacity" {
  alarm_name          = "outpost-s3-capacity-80pct"
  namespace           = "AWS/S3Outposts"
  metric_name         = "BucketSizeBytes"
  dimensions = {
    BucketName = aws_s3control_bucket.main.bucket
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 800000000000  # ~800 GB
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

## Step 8: replication configuration and role trust policy (moved from SKILL.md)

**Configure replication:**

```bash
aws s3control put-bucket-replication \
  --account-id 123456789012 \
  --bucket "arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-xxx/bucket/my-outpost-bucket" \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789012:role/S3OutpostsReplicationRole",
    "Rules": [{
      "Status": "Enabled",
      "Priority": 1,
      "Destination": {
        "Bucket": "arn:aws:s3:::cloud-destination-bucket"
      },
      "Filter": {}
    }]
  }'
```

**Replication role trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "s3-outposts.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## Step 10: capacity alarm (moved from SKILL.md)

**Create a capacity alarm:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "outpost-s3-capacity-80pct" \
  --namespace AWS/S3Outposts \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=my-outpost-bucket \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 800000000000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:outpost-alerts"
```

