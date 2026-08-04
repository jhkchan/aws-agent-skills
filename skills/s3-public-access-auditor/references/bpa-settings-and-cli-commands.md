# S3 Block Public Access — Settings and CLI Commands

Reference for the S3 Public-Access Auditor skill. Provides the full BPA
enablement commands and account-level vs bucket-level detail.

## The 4 BPA settings

S3 Block Public Access (BPA) has 4 independent settings. A bucket is
considered "BPA fully enabled" only when ALL 4 are `True` at BOTH the account
level and the bucket level.

- `BlockPublicAcls` — rejects PUT of public ACLs (READ/WRITE
  to AllUsers or AuthenticatedUsers). Existing public ACLs are
  ignored.
- `IgnorePublicAcls` — ignores all public ACLs on the bucket and
  objects. Existing public ACLs still appear in `get-bucket-acl`
  output but have no effect.
- `BlockPublicPolicy` — rejects PUT of bucket policies that grant
  public access (`Principal: "*"` with non-private actions).
- `RestrictPublicBuckets` — restricts access for buckets with
  public policies to only AWS service principals and authorized
  users within the bucket owner's account.

## Account-level BPA (applies to all buckets in the account)

```bash
aws s3control put-public-access-block \
  --profile default \
  --region us-east-1 \
  --account-id 123456789012 \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Bucket-level BPA (applies to a single bucket)

```bash
aws s3api put-public-access-block \
  --profile default \
  --region us-east-1 \
  --bucket <bucket-name> \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Verify current BPA state

```bash
# Bucket-level
aws s3api get-public-access-block \
  --profile default \
  --region us-east-1 \
  --bucket <bucket-name>

# Account-level
aws s3control get-public-access-block \
  --profile default \
  --region us-east-1 \
  --account-id 123456789012
```

## Remove a public ACL (set to private)

```bash
aws s3api put-bucket-acl \
  --profile default \
  --region us-east-1 \
  --bucket <bucket-name> \
  --acl private
```

## Remove a public bucket policy

```bash
aws s3api delete-bucket-policy \
  --profile default \
  --region us-east-1 \
  --bucket <bucket-name>
```

## CloudFront OAI replacement for public CDN access

Instead of a `Principal: "*"` bucket policy, use a CloudFront Origin Access
Identity:

```bash
# Create the OAI
aws cloudfront create-cloud-front-origin-access-identity \
  --cloud-front-origin-access-identity-config \
  CallerReference="$(date +%s)",Comment="OAI for <bucket-name>"

# Then attach a policy that grants s3:GetObject only to the OAI ARN:
# "Principal": { "CanonicalUser": "<OAI S3 canonical user id>" }
```

For newer setups, prefer Origin Access Control (OAC) over OAI — OAC supports
all request types and is the current AWS recommendation.

## Account-level precedence

Account-level BPA does NOT override bucket-level BPA — they are independent.
If account-level BPA is off but bucket-level BPA is fully enabled, that bucket
is protected at the bucket level. However, enabling account-level BPA as well
ensures all buckets (including future ones) are protected — defense-in-depth.

The skill's classification treats a bucket as SAFE when bucket-level BPA is
fully enabled (all 4 True), regardless of account-level state. This matches
AWS behavior: bucket-level BPA is evaluated per-bucket and is authoritative
for that bucket.
