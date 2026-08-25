# OAI Migration and SSE-KMS — CloudFront OAC Deployer

Deep reference on migrating from OAI to OAC with zero downtime
(transition bucket policy with dual grants, distribution cutover,
OAI cleanup), SSE-KMS configuration with OAC (KMS key policy
requirements, signing behavior constraints), and common migration
pitfalls. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## OAI to OAC migration

### Why migrate

OAC is the successor to OAI. Key advantages:
- **SSE-KMS support:** OAC can serve SSE-KMS-encrypted objects (OAI
  cannot — CloudFront gets 403 when trying to decrypt).
- **POST/PUT support:** OAC signs all HTTP methods (OAI only signs
  GET/HEAD).
- **Future-proofing:** AWS recommends OAC for all new distributions
  and may deprecate OAI.

### Zero-downtime migration flow

The key principle: **add the OAC before removing the OAI**. Both
access controls can coexist during the transition.

```text
Phase 1 — PREPARE (no traffic impact)
  1a. Create the OAC
  1b. Update the bucket policy to ADD the cloudfront.amazonaws.com
      grant (KEEP the existing OAI canonical user ID grant)
  → At this point, the bucket allows BOTH OAC and OAI access
  → The distribution still uses the OAI (no change to traffic)

Phase 2 — CUTOVER (brief deployment, no downtime)
  2a. Update the distribution origin to set OriginAccessControlId
      (KEEP the existing S3OriginConfig.OriginAccessIdentity / OAI)
  → The distribution now references BOTH OAC and OAI
  → OAC takes precedence for signing, but OAI is still configured
  → Distribution deploys — traffic continues flowing via OAC

Phase 3 — VERIFY (confirm OAC works)
  3a. Test CloudFront serves objects correctly (no 403)
  3b. Check CloudFront access logs for any errors
  3c. Verify from multiple edge locations if possible

Phase 4 — CLEANUP (no traffic impact after verification)
  4a. Remove the OAI from the distribution origin
      (set S3OriginConfig.OriginAccessIdentity to "")
  4b. Remove the OAI canonical user ID grant from the bucket policy
  4c. Delete the OAI resource
  → OAC is now the sole access control
```

### Phase 1 — bucket policy with dual grants

```bash
aws s3api put-bucket-policy --bucket my-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontOAC",
      "Effect": "Allow",
      "Principal": {"Service": "cloudfront.amazonaws.com"},
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
        }
      }
    },
    {
      "Sid": "AllowLegacyOAI",
      "Effect": "Allow",
      "Principal": {"CanonicalUser": "1a2b3c4d5e6f7g8h9i0j"},
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}'
```

### Finding the OAI canonical user ID

```bash
# Get the OAI canonical user ID
aws cloudfront get-cloud-front-origin-access-identity \
  --id E3OAIID1234 \
  --query 'CloudFrontOriginAccessIdentity.S3CanonicalUserId' --output text
```

### Phase 2 — distribution update

```bash
ETAG=$(aws cloudfront get-distribution-config \
  --id EDFDVBD6EXAMPLE --query 'ETag' --output text)

# In the distribution config JSON, set:
#   Origins.Items[0].OriginAccessControlId = "<new-oac-id>"
#   (keep Origins.Items[0].S3OriginConfig.OriginAccessIdentity as-is)
aws cloudfront update-distribution \
  --id EDFDVBD6EXAMPLE \
  --if-match "$ETAG" \
  --distribution-config file://phase2-dual-config.json
```

### Phase 4 — remove OAI

```bash
# 4a. Remove OAI from distribution
ETAG2=$(aws cloudfront get-distribution-config \
  --id EDFDVBD6EXAMPLE --query 'ETag' --output text)
# Set Origins.Items[0].S3OriginConfig.OriginAccessIdentity to ""
aws cloudfront update-distribution \
  --id EDFDVBD6EXAMPLE \
  --if-match "$ETAG2" \
  --distribution-config file://phase4-oac-only.json

# 4b. Remove OAI grant from bucket policy (only OAC statement remains)

# 4c. Delete the OAI
OAI_ETAG=$(aws cloudfront get-cloud-front-origin-access-identity-config \
  --id E3OAIID1234 --query 'ETag' --output text)
aws cloudfront delete-cloud-front-origin-access-identity \
  --id E3OAIID1234 \
  --if-match "$OAI_ETAG"
```

## SSE-KMS with OAC

### Requirements for SSE-KMS buckets

1. **OAC with `always-sign`** — S3 needs sigv4-signed requests to
   authorize KMS decryption.
2. **S3 bucket policy** — grants `cloudfront.amazonaws.com`
   `s3:GetObject` with `AWS:SourceArn` condition.
3. **KMS key policy** — grants `cloudfront.amazonaws.com`
   `kms:Decrypt` with `AWS:SourceArn` condition.

All three are required. Missing any one results in 403.

### Checking bucket encryption

```bash
aws s3api get-bucket-encryption --bucket my-secure-bucket \
  --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault' \
  --output table
# Expected: { SSEAlgorithm: aws:kms, KMSMasterKeyID: arn:aws:kms:... }
```

### KMS key policy for CloudFront

```bash
aws kms put-key-policy \
  --key-id arn:aws:kms:us-east-1:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab \
  --policy-name default \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowCloudFrontServicePrincipalKMSDecrypt",
        "Effect": "Allow",
        "Principal": {"Service": "cloudfront.amazonaws.com"},
        "Action": "kms:Decrypt",
        "Resource": "*",
        "Condition": {
          "StringEquals": {
            "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
          }
        }
      }
    ]
  }'
```

### Important KMS key policy notes

- The KMS key policy uses the SAME `cloudfront.amazonaws.com`
  principal and `AWS:SourceArn` condition as the S3 bucket policy.
- The `Resource` is `"*"` because KMS key policies are attached to
  the key itself (the key ARN is implied).
- If using a customer-managed KMS key (not AWS-managed), ensure the
  key policy also retains the account admin permissions so you don't
  lock yourself out.
- For AWS-managed KMS keys (`aws/s3`), you CANNOT modify the key
  policy — SSE-KMS with CloudFront OAC requires a customer-managed
  key (CMK).

### SSE-KMS + multi-distribution

For SSE-KMS buckets served by multiple distributions, the KMS key
policy must list ALL distribution ARNs (same pattern as the S3 bucket
policy):

```json
"Condition": {
  "StringEquals": {
    "AWS:SourceArn": [
      "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE",
      "arn:aws:cloudfront::111122223333:distribution/E2QWRUEXAMPLE2"
    ]
  }
}
```

## Terraform SSE-KMS example

```hcl
# KMS key for S3 SSE-KMS
resource "aws_kms_key" "s3_key" {
  description             = "KMS key for S3 SSE-KMS"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

# KMS key policy allowing CloudFront
resource "aws_kms_key_policy" "cloudfront_kms" {
  key_id = aws_kms_key.s3_key.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontKMSDecrypt"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "kms:Decrypt"
        Resource  = "*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.my_distribution.arn
          }
        }
      },
      # Keep admin access
      {
        Sid       = "EnableIAMUserPermissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::111122223333:root" }
        Action    = "kms:*"
        Resource  = "*"
      }
    ]
  })
}

# S3 bucket with SSE-KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "sse_kms" {
  bucket = aws_s3_bucket.my_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}
```

## Common migration pitfalls

### Pitfall 1: Removing OAI before OAC is verified

If you remove the OAI before confirming the OAC works, and the OAC is
misconfigured (e.g., bucket policy missing), CloudFront goes down.
Always verify after Phase 2 before proceeding to Phase 4.

### Pitfall 2: Forgetting the KMS key policy

For SSE-KMS buckets, the S3 bucket policy alone is not enough. The
KMS key policy must also grant `cloudfront.amazonaws.com`
`kms:Decrypt`. Without it, CloudFront gets 403 from KMS via S3.

### Pitfall 3: Using no-override with SSE-KMS

The `no-override` signing behavior does NOT work with SSE-KMS because
it depends on the viewer sending an Authorization header. For SSE-KMS
buckets, always use `always-sign`.

### Pitfall 4: AWS-managed KMS key

SSE-KMS using the AWS-managed key (`aws/s3`) does NOT allow modifying
the key policy. CloudFront OAC with SSE-KMS requires a customer-
managed key (CMK) so you can add the `cloudfront.amazonaws.com`
principal to the key policy.

### Pitfall 5: Bucket policy not updated after migration cleanup

After removing the OAI, ensure the OAI canonical user ID grant is
also removed from the bucket policy. Leaving it is a security risk if
the OAI is later recreated by a different process.

## Expert heuristic: sigv4 signing for SSE-KMS origins (moved from SKILL.md)

A baseline model may not consider signing behavior. The correct
heuristic recognizes that SSE-KMS-encrypted buckets require OAC to
sign every request with SigV4, because S3 needs the signed request
to authorize KMS decryption.

```text
Signing behavior options (OAC SigningBehavior):
  ├── always-sign  → CloudFront ALWAYS signs origin requests (sigv4)
  │     REQUIRED for: SSE-KMS buckets, POST/PUT requests
  │     Recommended for: all new OAC configurations
  ├── never-sign   → CloudFront NEVER signs (public S3 — rare)
  └── no-override  → CloudFront signs ONLY if viewer request
                    includes an Authorization header
                    Does NOT work for SSE-KMS
```

**Key implication:** for SSE-KMS buckets, always use `always-sign`.
Without sigv4-signed requests, S3 cannot authorize KMS decryption.
The KMS key policy must also grant `cloudfront.amazonaws.com`
`kms:Decrypt`.

## Step 6 — SSE-KMS verification and KMS key policy (moved from SKILL.md)

**Verify the bucket uses SSE-KMS:**

```bash
aws s3api get-bucket-encryption --bucket my-bucket \
  --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault' \
  --output table
# Expected: SSEAlgorithm: aws:kms, KMSMasterKeyID: arn:aws:kms:...
```

**Update the KMS key policy:**

```bash
aws kms put-key-policy \
  --key-id arn:aws:kms:us-east-1:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab \
  --policy-name default \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "AllowCloudFrontServicePrincipalKMSDecrypt",
      "Effect": "Allow",
      "Principal": {"Service": "cloudfront.amazonaws.com"},
      "Action": "kms:Decrypt",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
        }
      }
    }]
  }'
```

**Critical:** the KMS key policy uses the SAME
`cloudfront.amazonaws.com` principal and `AWS:SourceArn` condition
pattern as the S3 bucket policy. Both must be present for SSE-KMS.

## Step 8 — OAI to OAC migration (no downtime) (moved from SKILL.md)

Migrating from OAI to OAC can be done with zero downtime by adding
the OAC alongside the existing OAI before removing the OAI.

```text
Migration flow (zero downtime):
  1. Create the OAC (create-origin-access-control)
  2. Update the bucket policy to add cloudfront.amazonaws.com grant
     (KEEP the existing OAI canonical user ID grant during transition)
  3. Update the distribution origin to set OriginAccessControlId
     (KEEP the existing S3OriginConfig.OriginAccessIdentity / OAI)
     → Both OAC and OAI configured during transition
     → Distribution deploys — traffic continues flowing
  4. Verify CloudFront serves objects correctly (no 403)
  5. Remove the OAI from the distribution origin (set to empty)
  6. Remove the OAI canonical user ID from the bucket policy
  7. Delete the OAI (delete-origin-access-identity)
```

**Step 2 — bucket policy with BOTH grants during transition:**

```bash
# ADD the cloudfront.amazonaws.com OAC grant (KEEP existing OAI grant)
aws s3api put-bucket-policy --bucket my-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid":"AllowCloudFrontOAC","Effect":"Allow","Principal":{"Service":"cloudfront.amazonaws.com"},"Action":"s3:GetObject","Resource":"arn:aws:s3:::my-bucket/*","Condition":{"StringEquals":{"AWS:SourceArn":"arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"}}},
    {"Sid":"AllowLegacyOAI","Effect":"Allow","Principal":{"CanonicalUser":"<oai-canonical-user-id>"},"Action":"s3:GetObject","Resource":"arn:aws:s3:::my-bucket/*"}
  ]
}'
```

**Step 5 — remove OAI from distribution** (set
`S3OriginConfig.OriginAccessIdentity` to `""`, keep
`OriginAccessControlId`). **Step 6** — remove the legacy OAI statement
from the bucket policy. **Step 7** — delete the OAI:

```bash
aws cloudfront delete-origin-access-identity --id <oai-id> --if-match <etag>
```
