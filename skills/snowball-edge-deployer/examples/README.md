# End-to-End Example: Snowball Edge Import Job

A walkthrough showing how to use the `snowball-edge-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are creating a Snowball Edge import job to migrate 150 TB of
on-premises data to Amazon S3. The deployment needs:

- Job type: IMPORT (on-premises → S3)
- S3 destination bucket: my-migration-bucket (us-east-1)
- Device type: Edge Storage Optimized (210 TB usable)
- Shipping address: addr-aaaabbbb
- Shipping option: NEXT_DAY
- Transfer method: NFS with parallel copy

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-snowball-edge
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Snowball Edge import job to migrate 150 TB of data
      to S3 bucket my-migration-bucket in us-east-1. Use Edge
      Storage Optimized. Ship to address addr-aaaabbbb."
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SNOWBALL_EDGE: JID12345678-1234-4321-1234-123456789012 (IMPORT) — EDGE_STORAGE_OPTIMIZED
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Job type: Import (on-premises → S3)
  [✓] Device type: Edge Storage Optimized (210 TB usable)
  [✓] S3 bucket: my-migration-bucket (region: us-east-1) — destination
  [✓] Shipping address: addr-aaaabbbb — verified
  [✓] Snowball type: EDGE_STORAGE_OPTIMIZED
  [✓] Cluster mode: single device
  [✓] Data transfer plan: NFS parallel copy (16 threads)
  [✓] Return shipping: AWS-provided label in console
  [✓] Data validation: report will be available after device return
  [✓] Tags: Environment=migration, Project=data-lift
VERIFICATION_COMMANDS:
  aws snowball describe-job --job-id JID12345678-1234-4321-1234-123456789012 --region us-east-1
  aws snowball list-jobs --region us-east-1
```

---

## Step 3 — Job creation commands

```bash
# Create the import job
JOB_ID=$(aws snowball create-job \
  --job-type IMPORT \
  --resources S3Resources='[{BucketArn=arn:aws:s3:::my-migration-bucket}]' \
  --address-id addr-aaaabbbb \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --description "Data migration to S3" \
  --shipping-option NEXT_DAY \
  --notification JobStateChangesOnly=true \
  --region us-east-1 \
  --query 'JobId' --output text)

echo "Job ID: $JOB_ID"
```

---

## Step 4 — Device receipt and unlock (after delivery)

```bash
# Download manifest
aws snowball get-job-manifest \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'Manifest' --output text > manifest.bin

# Get unlock code
UNLOCK_CODE=$(aws snowball get-job-unlock-code \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'UnlockCode' --output text)

# Pair and unlock device
snowballEdge unlock-device \
  --device-ip-address 192.168.1.100 \
  --manifest-file manifest.bin \
  --unlock-code $UNLOCK_CODE \
  --endpoint https://192.168.1.100:9091

# Start NFS interface
snowballEdge start-service \
  --service-id nfs \
  --device-ip-address 192.168.1.100 \
  --manifest-file manifest.bin \
  --unlock-code $UNLOCK_CODE \
  --endpoint https://192.168.1.100:9091

# Mount NFS and copy data (parallel copy)
mount -t nfs -o nolock,hard 192.168.1.100:/nfs/path /mnt/snowball
find /data -type f | xargs -P 16 -I{} cp {} /mnt/snowball/
```

---

## Step 5 — Return and verify

```bash
# Stop NFS and power off
snowballEdge stop-service \
  --service-id nfs \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091

# Return device with AWS-provided shipping label
# Wait for AWS to process (check job status)
aws snowball describe-job \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'JobMetadata.JobState'

# After import completes, check data in S3
aws s3 ls s3://my-migration-bucket/ --recursive --summarize
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Data flow | Assumes real-time upload | Device → return → AWS uploads | Device is a shuttle, not a gateway |
| NFS start | Assumes NFS auto-starts | Must run start-service after unlock | NFS does not auto-start |
| Parallelism | Single-threaded copy | 16-thread parallel copy via xargs | 16x faster transfer |
| Return shipping | Forgets to return device | Return label in checklist | Data uploads only after return |
| Validation | No post-import check | Data validation report cited | Failed objects need re-transfer |

---

## Related artifacts

- **Skill definition:** `skills/snowball-edge-deployer/SKILL.md`
- **Import/export data flow guide:** `skills/snowball-edge-deployer/references/import-export-data-flow.md`
- **Cluster and compute guide:** `skills/snowball-edge-deployer/references/cluster-and-compute.md`
- **Slash command:** `commands/aws/deploy-snowball-edge.md`
- **Eval suite:** `skills/snowball-edge-deployer/evals/evals.json`
- **Legacy test cases:** `skills/snowball-edge-deployer/eval/test-cases.yaml`
