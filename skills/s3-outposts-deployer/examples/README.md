# End-to-End Example: S3 on Outposts Deployment

A walkthrough showing how to use the `s3-outposts-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an S3 bucket on an Outpost rack with a VPC
endpoint for access, an access point, one-way replication to a cloud
DR bucket, and capacity monitoring. The setup needs:

- Outpost: op-0abc123def456
- Bucket: my-outpost-bucket
- Endpoint: subnet subnet-abc123, SG sg-outpost-s3
- Access point: my-ap in VPC vpc-abc123
- Replication: Outpost to cloud (s3://cloud-dr-bucket)
- Versioning: enabled
- Tags: Environment=onprem, Application=data-lake

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-s3-outposts
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an S3 bucket on Outpost op-0abc123def456. I need an
      endpoint in subnet subnet-abc123. Replicate to cloud
      bucket s3://cloud-dr-bucket. Versioning enabled."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create s3 outposts bucket"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
S3_OUTPOST: my-outpost-bucket on op-0abc123def456
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Outpost: op-0abc123def456 — ACTIVE
  [✓] Endpoint: arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-0abc123def456/endpoint/abc-123 — Available
  [✓] Bucket: my-outpost-bucket (arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-0abc123def456/bucket/my-outpost-bucket)
  [✓] Access point: my-ap (regional)
  [✓] Storage class: STANDARD (only class available)
  [✓] Encryption: SSE-S3 (default)
  [✓] Versioning: Enabled
  [✓] Replication: Outpost → cloud (s3://cloud-dr-bucket)
  [✓] Object lock: Disabled
  [✓] Capacity alarm: outpost-s3-capacity-80pct
  [✓] Tags: Environment=onprem, Application=data-lake
VERIFICATION_COMMANDS:
  aws s3control list-regional-buckets --account-id 123456789012
  aws s3outposts list-endpoints
  aws cloudwatch get-metric-statistics --namespace AWS/S3Outposts --metric-name BucketSizeBytes ...
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the endpoint (mandatory for access)
ENDPOINT_ARN=$(aws s3outposts create-endpoint \
  --outpost-id op-0abc123def456 \
  --subnet-id subnet-abc123 \
  --security-group-id sg-outpost-s3 \
  --query 'EndpointArn' --output text)

# Step 2: Create the bucket on the Outpost
BUCKET_ARN=$(aws s3control create-bucket \
  --bucket "my-outpost-bucket" \
  --outpost-id op-0abc123def456 \
  --query 'BucketArn' --output text)

# Step 3: Enable versioning
aws s3control put-bucket-versioning \
  --account-id 123456789012 \
  --bucket "$BUCKET_ARN" \
  --versioning-configuration Status=Enabled

# Step 4: Create access point
aws s3control create-access-point \
  --name "my-ap" \
  --bucket "$BUCKET_ARN" \
  --vpc-configuration VpcId=vpc-abc123

# Step 5: Configure one-way replication to cloud
aws s3control put-bucket-replication \
  --account-id 123456789012 \
  --bucket "$BUCKET_ARN" \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789012:role/S3OutpostsReplicationRole",
    "Rules": [{
      "Status": "Enabled",
      "Priority": 1,
      "Destination": {"Bucket": "arn:aws:s3:::cloud-dr-bucket"},
      "Filter": {}
    }]
  }'

# Step 6: Create capacity alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "outpost-s3-capacity-80pct" \
  --namespace AWS/S3Outposts \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=my-outpost-bucket \
  --statistic Sum --period 300 --evaluation-periods 1 \
  --threshold 800000000000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:outpost-alerts"
```

---

## Step 4 — Post-deployment verification

```bash
# Verify bucket
aws s3control list-regional-buckets --account-id 123456789012

# Verify endpoint is Available
aws s3outposts list-endpoints

# Verify replication
aws s3control get-bucket-replication \
  --account-id 123456789012 \
  --bucket "$BUCKET_ARN"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Endpoint | Not created | VPC endpoint before bucket access | Without endpoint, bucket is inaccessible |
| Storage class | Assumes Glacier available | STANDARD only | Outpost supports only STANDARD |
| Encryption | Assumes KMS available | SSE-S3 only | KMS not supported on Outpost S3 |
| Replication | Assumes bidirectional | One-way (Outpost to cloud) | Cloud-to-Outpost not supported |
| Object lock | Can enable later | At creation only | Cannot enable after bucket creation |
| Lifecycle | Glacier transition | Expiration only | Cannot transition to cloud storage classes |

---

## Related artifacts

- **Skill definition:** `skills/s3-outposts-deployer/SKILL.md`
- **Endpoints guide:** `skills/s3-outposts-deployer/references/endpoints-and-networking.md`
- **Replication guide:** `skills/s3-outposts-deployer/references/replication-and-capacity.md`
- **Slash command:** `commands/aws/deploy-s3-outposts.md`
- **Eval suite:** `skills/s3-outposts-deployer/evals/evals.json`
- **Legacy test cases:** `skills/s3-outposts-deployer/eval/test-cases.yaml`
