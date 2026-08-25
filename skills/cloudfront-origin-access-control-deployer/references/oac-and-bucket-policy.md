# OAC and S3 Bucket Policy — CloudFront OAC Deployer

Deep reference on OAC creation parameters, S3 bucket policy patterns
for OAC (cloudfront.amazonaws.com principal, AWS:SourceArn vs
AWS:SourceAccount, multi-distribution SourceArn lists), signing
behavior selection (always-sign vs never-sign vs no-override), and
common bucket policy pitfalls. Loaded on demand by the skill — kept
out of the main SKILL.md body so the provisioning procedure stays
scannable.

## OAC creation parameters

### Full parameter reference

```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{
      "Name": "oac-my-bucket",
      "Description": "OAC for my-bucket S3 origin",
      "SigningProtocol": "sigv4",
      "SigningBehavior": "always-sign",
      "OriginAccessControlOriginType": "s3"
    }'
```

| Parameter | Value | Notes |
|---|---|---|
| `Name` | string | Identifier for the OAC (not the bucket name) |
| `Description` | string | Optional, human-readable |
| `SigningProtocol` | `sigv4` | The only supported value |
| `SigningBehavior` | `always-sign` / `never-sign` / `no-override` | Controls when CloudFront signs origin requests |
| `OriginAccessControlOriginType` | `s3` | The only supported value; OAC is S3-only |

### Listing and inspecting OACs

```bash
# List all OACs
aws cloudfront list-origin-access-controls

# Get details of a specific OAC
aws cloudfront get-origin-access-control --id E2QWRUOACID123

# Get the ETag (for updates/deletes)
aws cloudfront get-origin-access-control-config --id E2QWRUOACID123 \
  --query 'ETag' --output text
```

### Updating an OAC

```bash
ETAG=$(aws cloudfront get-origin-access-control-config \
  --id E2QWRUOACID123 --query 'ETag' --output text)

aws cloudfront update-origin-access-control \
  --id E2QWRUOACID123 \
  --if-match "$ETAG" \
  --origin-access-control-config \
    '{"Name":"oac-my-bucket-updated","Description":"Updated","SigningProtocol":"sigv4","SigningBehavior":"always-sign","OriginAccessControlOriginType":"s3"}'
```

### Deleting an OAC

```bash
aws cloudfront delete-origin-access-control \
  --id E2QWRUOACID123 \
  --if-match "$ETAG"
```

## S3 bucket policy patterns for OAC

### Pattern 1: Single distribution (recommended for production)

```json
{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowCloudFrontServicePrincipalReadOnly",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
      }
    }
  }
}
```

### Pattern 2: Multi-distribution to single bucket

```json
{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowMultipleDistributions",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::shared-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": [
          "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE",
          "arn:aws:cloudfront::111122223333:distribution/E2QWRUEXAMPLE2"
        ]
      }
    }
  }
}
```

### Pattern 3: Account-level (broader, simpler, less restrictive)

```json
{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowAccountDistributions",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceAccount": "111122223333"
      }
    }
  }
}
```

### Pattern 4: Read-write (POST/PUT via CloudFront)

```json
{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowCloudFrontReadWrite",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::my-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
      }
    }
  }
}
```

## AWS:SourceArn vs AWS:SourceAccount

| Condition key | Scope | Security | When to use |
|---|---|---|---|
| `AWS:SourceArn` | Specific distribution | Most restrictive | Production workloads |
| `AWS:SourceAccount` | All distributions in account | Broader | Simplicity in low-risk environments |

**Always prefer `AWS:SourceArn`** for production. `AWS:SourceAccount`
grants ALL distributions in the account, including any created in the
future without your knowledge.

## Signing behavior deep dive

### always-sign

CloudFront ALWAYS signs origin requests with SigV4, regardless of the
viewer request. This is the recommended behavior for all new OAC
configurations.

- Required for SSE-KMS-encrypted buckets
- Required for POST/PUT requests
- Works with private buckets (the default OAC use case)

### never-sign

CloudFront NEVER signs origin requests. The S3 bucket must be public
for CloudFront to read objects. This defeats the purpose of OAC and
is rarely used.

- Only for public buckets where you want OAC metadata but no signing
- Does NOT work with SSE-KMS

### no-override

CloudFront signs ONLY if the viewer request includes an Authorization
header. If the viewer does not send the header, CloudFront does not
sign.

- Use case: client-controlled access (signed URLs at the origin)
- Does NOT work with SSE-KMS (viewer may not send the header)
- Unreliable for automated access patterns

## Verifying the bucket policy

```bash
# Get the bucket policy
aws s3api get-bucket-policy --bucket my-bucket --output text --query Policy | jq .

# Verify the principal is cloudfront.amazonaws.com
aws s3api get-bucket-policy --bucket my-bucket --output text --query Policy \
  | jq '.Statement[].Principal.Service'
# Expected: "cloudfront.amazonaws.com"

# Verify the SourceArn condition
aws s3api get-bucket-policy --bucket my-bucket --output text --query Policy \
  | jq '.Statement[].Condition.StringEquals."AWS:SourceArn"'
# Expected: "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
```

## Common bucket policy pitfalls

### Pitfall 1: Using the OAC ID as principal

```json
// WRONG — S3 bucket policies do not understand OAC IDs
"Principal": {"Service": "oac:E2QWRUOACID123"}

// CORRECT — use the CloudFront service principal
"Principal": {"Service": "cloudfront.amazonaws.com"}
```

### Pitfall 2: Missing the condition

Without the `AWS:SourceArn` condition, ANY CloudFront distribution in
ANY account could access the bucket (if they knew the bucket name).

```json
// WRONG — no condition, too broad
{
  "Principal": {"Service": "cloudfront.amazonaws.com"},
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/*"
}
```

### Pitfall 3: Wrong distribution ARN

The ARN must match the distribution exactly:
`arn:aws:cloudfront::<account-id>:distribution/<distribution-id>`

Common mistakes: using the distribution's domain name instead of the
ID, or using the wrong account ID.

## Terraform examples

```hcl
# OAC resource
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "oac-my-bucket"
  description                       = "OAC for my-bucket"
  signing_protocol                  = "sigv4"
  signing_behavior                  = "always"
  origin_access_control_origin_type = "s3"
}

# S3 bucket policy
resource "aws_s3_bucket_policy" "cloudfront_access" {
  bucket = aws_s3_bucket.my_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = {
      Sid       = "AllowCloudFrontServicePrincipalReadOnly"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.my_bucket.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.my_distribution.arn
        }
      }
    }
  })
}

# Distribution origin referencing OAC
resource "aws_cloudfront_distribution" "my_distribution" {
  origin {
    domain_name              = aws_s3_bucket.my_bucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
    origin_id                = "my-s3-origin"
  }

  # ... cache behavior, viewer certificate, etc.
}
```

## Expert heuristic: bucket policy uses cloudfront.amazonaws.com (moved from SKILL.md)

A baseline model may use the OAC ID in the bucket policy. The correct
heuristic recognizes that the bucket policy grants the
`cloudfront.amazonaws.com` service principal — NOT the OAC ID — with
a condition matching the distribution ARN.

```json
{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowCloudFrontServicePrincipalReadOnly",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
      }
    }
  }
}
```

**Key implication:** the principal is always `cloudfront.amazonaws.com`
and the `AWS:SourceArn` condition restricts which distribution can
access the bucket. Using the OAC ID as the principal does not work.

## Step 3: Multi-distribution SourceArn list (moved from SKILL.md)

**For multi-distribution to single bucket**, list all ARNs:

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

## Step 7 — Multi-distribution to single bucket (moved from SKILL.md)

When multiple CloudFront distributions serve from a single S3 bucket,
each distribution has its own OAC, but the bucket policy must list
ALL distribution ARNs in the `AWS:SourceArn` condition.

```bash
aws s3api put-bucket-policy --bucket shared-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowMultipleCloudFrontDistributions",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::shared-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": [
          "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE",
          "arn:aws:cloudfront::111122223333:distribution/E2QWRUEXAMPLE2",
          "arn:aws:cloudfront::111122223333:distribution/E3EXAMPLE3XXX"
        ]
      }
    }
  }
}'
```

**Alternative: `AWS:SourceAccount`** grants ALL distributions in the
account access. Simpler to manage but less restrictive. Prefer listing
individual ARNs for production.

**Each distribution should still have its own OAC** — the OAC is per-
distribution, not per-bucket.
