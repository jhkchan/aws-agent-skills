# End-to-End Example: S3 Directory Bucket Deployment (ML Cache)

A walkthrough showing how to use the `s3-directory-bucket-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying an S3 Express One Zone directory bucket as a
low-latency ML training data cache. EC2 GPU instances in `us-east-1a`
need single-digit-millisecond read access to cached training shards.
The workload does not require cross-region replication, versioning, or
Object Lock.

- Base bucket name: `ml-cache-data`
- AZ: `us-east-1a` (resolve to AZ ID `use1-az1`)
- Region: `us-east-1`
- Encryption: SSE-KMS
- Compute: 4 x c7n.large in subnet `subnet-aaa` (AZ `use1-az1`)
- Account: `111111111111`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-s3-directory-bucket
```

Then paste the directory bucket requirements.

### Option B: Natural language

> Create an S3 Express One Zone directory bucket called ml-cache-data
> in us-east-1a. Use SSE-KMS encryption. My EC2 instances are in
> subnet subnet-aaa (use1-az1). This is a ML training data cache, no
> CRR or versioning needed.

---

## Step 2 — Skill pre-flight

The skill validates prerequisites:

1. AZ ID resolution: `us-east-1a` resolves to `use1-az1` (verified via
   `ec2 describe-availability-zones`)
2. Bucket name format: `ml-cache-data--use1-az1--x-s3` (double-dash,
   `--x-s3` suffix)
3. Compute placement: 4 x c7n.large in subnet `subnet-aaa`, confirmed
   in AZ `use1-az1` (matches bucket AZ)
4. Encryption: SSE-KMS key in `us-east-1`
5. Unsupported features: CRR=no, versioning=no, Object Lock=no —
   confirmed absent

All prerequisites pass.

---

## Step 3 — Expected output

```text
DIRECTORY_BUCKET_SPEC: ml-cache-data--use1-az1--x-s3
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] AZ ID resolved: use1-az1 (from AZ name us-east-1a)
  [✓] Directory bucket name format: ml-cache-data--use1-az1--x-s3 verified (double-dash delimited, --x-s3 suffix)
  [✓] Directory bucket created: BucketType=Directory confirmed via list-buckets
  [✓] Encryption: SSE-KMS (arn:aws:kms:us-east-1:111111111111:key/abc-123)
  [✓] Bucket policy: s3express ARN format (arn:aws:s3express:us-east-1:111111111111:ml-cache-data--use1-az1--x-s3)
  [✓] Zone-affinity compute: 4 x c7n.large in AZ use1-az1 (subnet subnet-aaa)
  [N/A] Table bucket: not applicable (object-level workload)
  [✓] Unsupported features confirmed absent: CRR=no, versioning=no, Object Lock=no
VERIFICATION_COMMANDS:
  aws ec2 describe-availability-zones --zone-names us-east-1a --query 'AvailabilityZones[0].[ZoneName,ZoneId]' --output text
  aws s3api list-buckets --query 'Buckets[?Name==`ml-cache-data--use1-az1--x-s3`]' --output json
  aws s3api get-bucket-encryption --bucket ml-cache-data--use1-az1--x-s3
  aws s3api get-bucket-policy --bucket ml-cache-data--use1-az1--x-s3
  aws ec2 describe-instances --filters "Name=tag:Name,Values=zone-affinity-app" --query 'Reservations[].Instances[].[InstanceId,Placement.AvailabilityZoneId]' --output table
```

---

## Step 4 — Provisioning commands

```bash
# Resolve AZ ID
aws ec2 describe-availability-zones \
  --zone-names us-east-1a \
  --query 'AvailabilityZones[0].[ZoneName,ZoneId]' --output text

# Create the directory bucket
aws s3api create-directory-bucket \
  --bucket ml-cache-data--use1-az1--x-s3 \
  --data-redundancy SingleAvailabilityZone \
  --region us-east-1

# Set SSE-KMS encryption
aws s3api put-bucket-encryption \
  --bucket ml-cache-data--use1-az1--x-s3 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:111111111111:key/abc-123"
      }
    }]
  }'

# Set bucket policy (s3express ARN format)
aws s3api put-bucket-policy \
  --bucket ml-cache-data--use1-az1--x-s3 \
  --policy file://directory-bucket-policy.json
```

---

## Step 5 — Post-deployment verification

```bash
# Verify bucket type is Directory (not general-purpose)
aws s3api list-buckets \
  --query 'Buckets[?Name==`ml-cache-data--use1-az1--x-s3`]' --output json

# Verify encryption
aws s3api get-bucket-encryption --bucket ml-cache-data--use1-az1--x-s3

# Verify compute AZ matches bucket AZ
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=zone-affinity-app" \
  --query 'Reservations[].Instances[].[InstanceId,Placement.AvailabilityZoneId]' \
  --output table

# Latency probe (from zone-affinity compute — should be single-digit ms)
time aws s3 ls s3://ml-cache-data--use1-az1--x-s3/ --region us-east-1
```

---

## Common pitfalls to verify after deployment

1. **Bucket was created with `create-directory-bucket`, not
   `create-bucket`.** `create-bucket` silently creates a standard S3
   bucket with no Express One Zone benefits. Verify `BucketType:
   Directory` in `list-buckets` output.

2. **Compute is in the same AZ as the bucket.** A directory bucket
   exists in exactly one AZ. Compute in a different AZ pays cross-AZ
   transfer fees ($0.01/GB each way) and sees 10x higher latency with
   no error. Verify AZ IDs match.

3. **Bucket policy uses `s3express` ARN format.** A standard `s3:::`
   ARN matches nothing on a directory bucket. Verify the policy uses
   `arn:aws:s3express:<region>:<account>:<bucket>`.

4. **No unsupported features are configured.** Directory buckets do
   NOT support CRR, versioning, Object Lock, or Transfer Acceleration.
   Confirm these are absent in the workload requirements.
