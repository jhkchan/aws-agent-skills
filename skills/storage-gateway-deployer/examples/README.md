# End-to-End Example: Storage Gateway Deployment

A walkthrough showing how to use the `storage-gateway-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying an S3 File Gateway with an NFS file share mapping
to an S3 bucket, with cache and upload buffer sized independently.
The deployment needs:

- Gateway name: prod-s3-file-gateway
- Gateway type: S3 File Gateway (FILE_S3)
- Region: us-east-1
- S3 bucket: my-data-bucket (us-east-1)
- Cache: 500 GB (separate physical disk)
- Upload buffer: 300 GB (separate physical disk)
- NFS file share: client list 10.0.0.0/16
- Default storage class: S3_STANDARD

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-storage-gateway
```

Then paste the requirements.

### Option B: Natural language

```
You: "Deploy an S3 File Gateway in us-east-1 with an NFS file share.
      Gateway name: prod-s3-file-gateway. S3 bucket: my-data-bucket.
      Cache: 500 GB. Upload buffer: 300 GB. NFS clients: 10.0.0.0/16."
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
STORAGE_GATEWAY: prod-s3-file-gateway (FILE_S3) — arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Gateway type: S3 File Gateway
  [✓] Activation: arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA — RUNNING
  [✓] Gateway region: us-east-1 (matches S3 bucket region: us-east-1)
  [✓] Cache: disk-aaa (500 GB) — allocated
  [✓] Upload buffer: disk-bbb (300 GB) — allocated
  [✓] S3 bucket: my-data-bucket (region: us-east-1)
  [✓] IAM role: arn:aws:iam::123456789012:role/StorageGatewayS3Role
  [✓] File share (NFS): share-AAAAA → s3://my-data-bucket (clients: 10.0.0.0/16)
  [✓] Default storage class: S3_STANDARD
  [✓] Bandwidth rate limit: scheduled (business: 50 Mbps, off-hours: 500 Mbps)
  [✓] CloudWatch: CacheHitPercent alarm at 80%
  [✓] Tags: Environment=production
VERIFICATION_COMMANDS:
  aws storagegateway describe-gateway-information --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA --region us-east-1
  aws storagegateway list-file-shares --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Activate the gateway
GATEWAY_ARN=$(aws storagegateway activate-gateway \
  --activation-key ABCDE-12345-FGHIJ-67890-KLMNO \
  --gateway-name prod-s3-file-gateway \
  --gateway-timezone "GMT-5:00" \
  --gateway-region us-east-1 \
  --gateway-type FILE_S3 \
  --tags Key=Environment,Value=production \
  --region us-east-1 \
  --query 'GatewayARN' --output text)

# Step 2: Allocate cache disk (separate physical disk)
aws storagegateway add-cache \
  --gateway-arn "$GATEWAY_ARN" \
  --disk-ids disk-aaa \
  --region us-east-1

# Step 3: Allocate upload buffer (separate physical disk)
aws storagegateway add-upload-buffer \
  --gateway-arn "$GATEWAY_ARN" \
  --disk-ids disk-bbb \
  --region us-east-1

# Step 4: Create NFS file share
aws storagegateway create-nfs-file-share \
  --client-token unique-token-12345 \
  --gateway-arn "$GATEWAY_ARN" \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::my-data-bucket \
  --default-storage-class S3_STANDARD \
  --client-list 10.0.0.0/16 \
  --region us-east-1

# Step 5: Set bandwidth rate limit schedule
aws storagegateway update-bandwidth-rate-limit-schedule \
  --gateway-arn "$GATEWAY_ARN" \
  --bandwidth-rate-limit-schedules \
    BandwidthRateLimitIntervals=[{StartHourOfDay=9,EndHourOfDay=18,BitsPerSecondLimit=50000000},{StartHourOfDay=18,EndHourOfDay=9,BitsPerSecondLimit=500000000}] \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify gateway is running
aws storagegateway describe-gateway-information \
  --gateway-arn "$GATEWAY_ARN" \
  --query 'GatewayState' --region us-east-1

# Verify file share is available
aws storagegateway list-file-shares \
  --gateway-arn "$GATEWAY_ARN" \
  --query 'FileShareInfoList[0].FileShareStatus' --region us-east-1

# Verify cache and buffer allocation
aws storagegateway list-local-disks \
  --gateway-arn "$GATEWAY_ARN" \
  --query 'Disks[*].{DiskId:DiskId,AllocationType:DiskAllocationType,SizeInBytes:DiskSizeInBytes}' \
  --region us-east-1 --output table
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Cache vs upload buffer | Conflated as "local disk" | Sized independently (cache=reads, buffer=writes) | Different I/O patterns; undersized either causes stalls |
| Region alignment | Not checked | Gateway region matches S3 bucket region | Cross-region mismatch causes data transfer charges |
| NFS client list | Unrestricted | Restricted to known CIDR blocks | Unrestricted shares are a security risk |
| Bandwidth schedule | Not configured | Business/off-hours schedule | Prevents internet link saturation |
| CloudWatch monitoring | Not configured | CacheHitPercent alarm at 80% | Low hit ratio = undersized cache |

---

## Related artifacts

- **Skill definition:** `skills/storage-gateway-deployer/SKILL.md`
- **Cache and buffer guide:** `skills/storage-gateway-deployer/references/cache-and-buffer-sizing.md`
- **File share and SMB guide:** `skills/storage-gateway-deployer/references/file-share-and-smb.md`
- **Slash command:** `commands/aws/deploy-storage-gateway.md`
- **Eval suite:** `skills/storage-gateway-deployer/evals/evals.json`
- **Legacy test cases:** `skills/storage-gateway-deployer/eval/test-cases.yaml`
