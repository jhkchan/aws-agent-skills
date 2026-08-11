# End-to-End Example: S3 Bucket Policy Deployment

A walkthrough showing how to use the `s3-bucket-policy-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an S3 bucket policy for a shared data bucket.
The policy needs:

- HTTPS-only enforcement (aws:SecureTransport Deny with Bool)
- Cross-account access for a partner (role ARN + ExternalId)
- CloudFront OAC for CDN origin access
- ACLs disabled (BucketOwnerEnforced)
- Block Public Access (all 4 settings)

Bucket: `prod-shared-data`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-s3-bucket-policy
```

Then paste the requirements.

### Option B: Natural language

```
You: "Attach a bucket policy to prod-shared-data with HTTPS-only
      Deny, cross-account access for partner 998877665544 with
      ExternalId, and CloudFront OAC for distribution
      E123ABCDEF456. Account 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "attach s3 bucket policy"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
BUCKET_POLICY: prod-shared-data (3 statements, 1.8 KB)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Bucket exists: prod-shared-data
  [✓] Policy version: 2012-10-17
  [✓] Policy size: 1.8 KB (< 20 KB limit)
  [✓] HTTPS-only (aws:SecureTransport Deny with Bool): present
  [✓] Cross-account: 998877665544 (role/PartnerRole, external-id: partner-ext-abc123)
  [✓] CloudFront OAC: distribution E123ABCDEF456
  [✓] ACLs disabled: BucketOwnerEnforced
  [✓] Block Public Access: all 4 settings True
VERIFICATION_COMMANDS:
  aws s3api get-bucket-policy --bucket prod-shared-data
  aws s3api get-public-access-block --bucket prod-shared-data
  aws s3api get-bucket-ownership-controls --bucket prod-shared-data
  aws cloudfront get-origin-access-control --id E123ABCDEF456
```

---

## Step 3 — Provisioning commands

```bash
# Step 0: Verify bucket exists and check BPA
aws s3api head-bucket --bucket prod-shared-data
aws s3api get-public-access-block --bucket prod-shared-data

# Step 1: Disable ACLs
aws s3api put-bucket-ownership-controls \
  --bucket prod-shared-data \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]

# Step 2: Apply the bucket policy
aws s3api put-bucket-policy \
  --bucket prod-shared-data \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DenyInsecureTransport",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": ["arn:aws:s3:::prod-shared-data", "arn:aws:s3:::prod-shared-data/*"],
        "Condition": { "Bool": { "aws:SecureTransport": "false" } }
      },
      {
        "Sid": "AllowCrossAccountWithExternalId",
        "Effect": "Allow",
        "Principal": { "AWS": "arn:aws:iam::998877665544:role/PartnerRole" },
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::prod-shared-data", "arn:aws:s3:::prod-shared-data/shared/*"],
        "Condition": { "StringEquals": { "aws:ExternalId": "partner-ext-abc123" } }
      },
      {
        "Sid": "AllowCloudFrontOAC",
        "Effect": "Allow",
        "Principal": { "Service": "cloudfront.amazonaws.com" },
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::prod-shared-data/*",
        "Condition": { "StringEquals": { "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/E123ABCDEF456" } }
      }
    ]
  }'

# Step 3: Enable Block Public Access
aws s3api put-public-access-block \
  --bucket prod-shared-data \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the bucket policy
aws s3api get-bucket-policy --bucket prod-shared-data \
  --query Policy --output text | python3 -m json.tool

# Verify Block Public Access
aws s3api get-public-access-block --bucket prod-shared-data

# Verify ownership controls (ACLs disabled)
aws s3api get-bucket-ownership-controls --bucket prod-shared-data

# Verify CloudFront OAC
aws cloudfront get-origin-access-control --id E123ABCDEF456
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| SecureTransport operator | StringNotEquals (fragile) | Bool (canonical) | Bool is the correct operator for boolean keys |
| Cross-account principal | `:root` (entire account) | specific role ARN | `:root` delegates to ALL identities in the account |
| ExternalId | Not included | aws:ExternalId condition | Prevents the confused-deputy problem |
| CloudFront principal | OAI canonical user ID (legacy) | cloudfront.amazonaws.com service (OAC) | OAC supports SSE-KMS; OAI is deprecated |
| AWS:SourceArn | Not included | distribution ARN condition | Without it, ANY distribution in the account can access |
| ACLs | Still enabled (legacy) | BucketOwnerEnforced | Disables ACLs; policy is the sole access mechanism |
| Object ARN | Omitted (only bucket ARN) | Both bucket + object ARN | Object actions need the `/*` ARN |

---

## Related artifacts

- **Skill definition:** `skills/s3-bucket-policy-deployer/SKILL.md`
- **Policy patterns deep dive:** `skills/s3-bucket-policy-deployer/references/policy-patterns.md`
- **Provisioning CLI commands:** `skills/s3-bucket-policy-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-s3-bucket-policy.md`
- **Eval suite:** `skills/s3-bucket-policy-deployer/evals/evals.json`
- **Legacy test cases:** `skills/s3-bucket-policy-deployer/eval/test-cases.yaml`
