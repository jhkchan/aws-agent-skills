# Provisioning CLI Commands — S3 Outposts Deployer

Copy-pasteable provisioning commands moved from SKILL.md. Load on demand.

## Step 3: bucket creation (moved from SKILL.md)

```bash
BUCKET_ARN=$(aws s3control create-bucket \
  --bucket "my-outpost-bucket" \
  --outpost-id op-0abc123def456 \
  --query 'BucketArn' --output text)

echo "Bucket ARN: $BUCKET_ARN"
```

**With object lock enabled at creation:**

```bash
BUCKET_ARN=$(aws s3control create-bucket \
  --bucket "my-worm-bucket" \
  --outpost-id op-0abc123def456 \
  --object-lock-enabled-for-bucket \
  --query 'BucketArn' --output text)
```

**Bucket ARN format for Outposts:**

```text
arn:aws:s3-outposts:<region>:<account>:outpost/op-xxx/bucket/my-outpost-bucket
```

## Step 4: outpost access point (moved from SKILL.md)

**Create an outpost access point:**

```bash
AP_ARN=$(aws s3control create-access-point \
  --name "my-ap" \
  --bucket "arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-xxx/bucket/my-outpost-bucket" \
  --vpc-configuration VpcId=vpc-abc123 \
  --query 'AccessPointArn' --output text)
```

**Access point types:**

| Type | Description |
|---|---|
| Outpost access point | Resolves to the Outpost endpoint; used for on-prem access |
| Regional access point | Regional endpoint that routes to the Outpost bucket |

