# End-to-End Example: S3 Secure Bucket Deployment

A walkthrough showing how to use the `s3-secure-bucket-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are setting up a new production data bucket for a customer-facing
application. The bucket needs:

- Block Public Access (account + bucket level)
- SSE-KMS encryption with a customer-managed key
- Object Ownership = BucketOwnerEnforced (no ACLs)
- Versioning enabled
- HTTPS-only + SSE-KMS upload enforcement policy
- Access logging to a central logging bucket
- Lifecycle: STANDARD_IA at 30 days, GLACIER at 90 days
- Tags for cost allocation

Bucket name: `prod-customer-uploads-2024`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-s3-secure-bucket
```

Then paste the bucket requirements.

### Option B: Natural language

```
You: "Provision a production S3 bucket named prod-customer-uploads-2024
      in us-east-1. Use SSE-KMS with alias/prod-s3-key. Enable versioning,
      access logging to s3-access-logs-prod, lifecycle: STANDARD_IA@30d,
      GLACIER@90d. Tags: Environment=production, Workload=app-uploads.
      Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a secure s3 bucket"
```

Output:

```
[Phase: Deploy | Skills routed: s3-secure-bucket-deployer]

Primary route: s3-secure-bucket-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

The skill walks its 10-step provisioning procedure and emits the
deterministic checklist:

```text
BUCKET: prod-customer-uploads-2024
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]        Block Public Access — bucket level (all 4 settings)
  [✓]        Block Public Access — account level (defense-in-depth)
  [✓]        Default encryption — SSE-KMS (alias/prod-s3-key, BucketKeyEnabled)
  [✓]        Object Ownership — BucketOwnerEnforced (ACLs disabled)
  [✓]        Versioning — Enabled
  [OPTIONAL] MFA Delete — Not enabled (recommend for sensitive data)
  [✓]        Bucket policy — HTTPS-only (aws:SecureTransport Deny)
  [✓]        Bucket policy — SSE-KMS upload enforcement
  [✓]        Access logging — Target: s3-access-logs-prod, Prefix: s3/prod-customer-uploads-2024/
  [OPTIONAL] CloudTrail data events — Not configured
  [✓]        Lifecycle — STANDARD_IA@30d → GLACIER@90d, expire noncurrent@180d
  [OPTIONAL] Replication — Not configured
  [✓]        Tags — Environment=production, Workload=app-uploads
VERIFICATION_COMMANDS:
  aws s3api get-public-access-block --bucket prod-customer-uploads-2024
  aws s3api get-bucket-encryption --bucket prod-customer-uploads-2024
  aws s3api get-bucket-ownership-controls --bucket prod-customer-uploads-2024
  aws s3api get-bucket-versioning --bucket prod-customer-uploads-2024
  aws s3api get-bucket-policy --bucket prod-customer-uploads-2024
  aws s3api get-bucket-logging --bucket prod-customer-uploads-2024
  aws s3api get-bucket-lifecycle-configuration --bucket prod-customer-uploads-2024
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Create bucket + BPA
aws s3api create-bucket --bucket prod-customer-uploads-2024 --region us-east-1

aws s3api put-public-access-block \
  --bucket prod-customer-uploads-2024 \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3control put-public-access-block \
  --account-id 123456789012 \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Step 2: SSE-KMS encryption with Bucket Key
aws s3api put-bucket-encryption \
  --bucket prod-customer-uploads-2024 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:123456789012:alias/prod-s3-key"
      },
      "BucketKeyEnabled": true
    }]
  }'

# Step 3: Object Ownership — disable ACLs
aws s3api put-bucket-ownership-controls \
  --bucket prod-customer-uploads-2024 \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]

# Step 4: Versioning
aws s3api put-bucket-versioning \
  --bucket prod-customer-uploads-2024 \
  --versioning-configuration Status=Enabled

# Step 5: Bucket policy — HTTPS + SSE-KMS enforcement
aws s3api put-bucket-policy \
  --bucket prod-customer-uploads-2024 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "EnforceHTTPSConnections",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::prod-customer-uploads-2024",
          "arn:aws:s3:::prod-customer-uploads-2024/*"
        ],
        "Condition": {"Bool": {"aws:SecureTransport": false}}
      },
      {
        "Sid": "DenyUnEncryptedObjectUploads",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::prod-customer-uploads-2024/*",
        "Condition": {"StringNotEquals": {"s3:x-amz-server-side-encryption": "aws:kms"}}
      }
    ]
  }'

# Step 6: Access logging
aws s3api put-bucket-logging \
  --bucket prod-customer-uploads-2024 \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "s3-access-logs-prod",
      "TargetPrefix": "s3/prod-customer-uploads-2024/"
    }
  }'

# Step 7: Lifecycle
aws s3api put-bucket-lifecycle-configuration \
  --bucket prod-customer-uploads-2024 \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "transition-current",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER"}
        ]
      },
      {
        "ID": "expire-noncurrent",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "NoncurrentVersionExpiration": {"NoncurrentDays": 180}
      }
    ]
  }'

# Step 8: Tags
aws s3api put-bucket-tagging \
  --bucket prod-customer-uploads-2024 \
  --tagging '{
    "TagSet": [
      {"Key": "Environment", "Value": "production"},
      {"Key": "Workload", "Value": "app-uploads"}
    ]
  }'
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# BPA — should show all 4 settings as True
aws s3api get-public-access-block --bucket prod-customer-uploads-2024

# Encryption — should show SSE-KMS with BucketKeyEnabled: true
aws s3api get-bucket-encryption --bucket prod-customer-uploads-2024

# Ownership — should show BucketOwnerEnforced
aws s3api get-bucket-ownership-controls --bucket prod-customer-uploads-2024

# Versioning — should show Status: Enabled
aws s3api get-bucket-versioning --bucket prod-customer-uploads-2024

# Policy — should show both Deny statements
aws s3api get-bucket-policy --bucket prod-customer-uploads-2024

# Logging — should show LoggingEnabled with target bucket
aws s3api get-bucket-logging --bucket prod-customer-uploads-2024

# Lifecycle — should show transition and noncurrent rules
aws s3api get-bucket-lifecycle-configuration --bucket prod-customer-uploads-2024
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Object Ownership | Not set (defaults to ObjectWriter) | BucketOwnerEnforced | ObjectWriter honors ACLs — the second-most-common S3 data leak vector. BucketOwnerEnforced disables ACLs at the API layer. |
| S3 Bucket Keys | Not enabled | BucketKeyEnabled: true | Without Bucket Keys, every upload triggers a KMS GenerateDataKey call. At scale, KMS throttling (5,500 req/s) blocks uploads. Bucket Keys reduce KMS calls by ~99%. |
| SSE-KMS enforcement policy | Not included | Deny s3:PutObject where SSE != aws:kms | Default encryption does NOT prevent clients from overriding the header. The enforcement policy makes SSE-KMS mandatory for all uploads. |
| Noncurrent version expiration | Not included | NoncurrentVersionExpiration: 180d | Versioning stores every version indefinitely. Without noncurrent expiration, storage costs grow without bound. |
| Account-level BPA | Not included | Enabled as defense-in-depth | Account-level BPA protects ALL buckets including future ones created by automation that skips bucket-level BPA. |
| Logging bucket policy | Not included | s3:PutObject grant to logging.s3.amazonaws.com | With BucketOwnerEnforced on the logging bucket, ACLs are disabled. The log-delivery service principal needs a bucket-policy grant to write logs. |

---

## Related artifacts

- **Skill definition:** `skills/s3-secure-bucket-deployer/SKILL.md`
- **Provisioning CLI commands:** `skills/s3-secure-bucket-deployer/references/provisioning-cli-commands.md`
- **Encryption and lifecycle guide:** `skills/s3-secure-bucket-deployer/references/encryption-and-lifecycle-guide.md`
- **Slash command:** `commands/aws/deploy-s3-secure-bucket.md`
- **Eval suite:** `skills/s3-secure-bucket-deployer/evals/evals.json`
- **Legacy test cases:** `skills/s3-secure-bucket-deployer/eval/test-cases.yaml`
