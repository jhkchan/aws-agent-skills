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

## Remediation guidance per verdict (moved from SKILL.md)

For **PUBLIC** buckets (policy-based, read-only):

1. Enable BPA at both account and bucket level (all 4 settings True).
2. Remove or restrict the public-read policy statement.
3. If public CDN access is intended, use CloudFront with Origin Access
   Control (OAC — the current AWS recommendation; OAI is legacy but
   still supported) instead of a bucket-level public policy.

For **PUBLIC** buckets (policy-based, write-capable — CRITICAL):

1. Enable BPA at both account and bucket level IMMEDIATELY (this is
   the fastest containment — it blocks the public policy in seconds).
2. After containment, audit CloudTrail (`s3:PutObject`,
   `s3:DeleteObject` events on the bucket) for the window of exposure
   to identify unauthorized writes. Use CloudTrail Lake event data
   stores or Athena queries on the `CloudTrail` S3 bucket.
3. Rotate any keys or credentials that may have been deposited in the
   bucket.

For **PUBLIC** buckets (ACL-based):

1. Enable BPA at both account and bucket level (all 4 settings True).
2. Remove the AllUsers / AuthenticatedUsers ACL grant:
   `aws s3api put-bucket-acl --bucket <name> --acl private`.

For **AMBIGUOUS** buckets:

1. Enable BPA (all 4 settings) as defense-in-depth — the condition
   protects now but a policy edit could remove it.
2. Replace the Allow-based restricted policy with an explicit Deny
   (deny all except the trusted VPCe/VPC/account) — Deny statements
   cannot be accidentally widened by adding a new Allow.
3. If the condition is `aws:sourceIp` on a public CIDR, treat the
   bucket as effectively PUBLIC (the CIDR restriction is not a real
   boundary if it covers the open internet or a broad ISP range) and
   apply the PUBLIC remediation path.
4. Flag for security team review to validate the condition is still
   correct and that the named VPCe/VPC still exists.

For **SAFE** buckets (BPA off, no public configs):

1. No remediation required for current exposure.
2. Recommend enabling BPA (all 4 settings) as defense-in-depth.
3. If website hosting is enabled and BPA is off, recommend either
   enabling BPA + CloudFront OAC for public content, or disabling
   website hosting if the bucket should be private.

For **SAFE** buckets (BPA fully enabled):

1. No remediation required. BPA is authoritative.

## Remediation for Access-Point-exposed buckets (moved from SKILL.md)

1. Tighten or replace the offending AP policy. Prefer replacing the
   wildcard Allow with a `Principal` listing the specific IAM role(s)
   or service(s) that need access through the AP.
2. Enable BPA at the account level (covers bucket and AP surfaces).
3. If public access through the AP is genuinely required (e.g., a public
   download endpoint), front the AP with CloudFront OAC rather than
   exposing it via `Principal: "*"`.
4. For MRAP, audit the policy at the global ARN — it propagates to all
   underlying regional buckets.

## Remediation for partial-BPA buckets (moved from SKILL.md)

1. Set the remaining BPA setting(s) to True at the SAME scope as the
   existing ones (or escalate to account-level for consistency).
2. If the gap is `IgnorePublicAcls`, note that existing public ACLs
   only become inert AFTER this is set — the grant is still present in
   `get-bucket-acl` output and will be re-honored if `IgnorePublicAcls`
   is later unset. Recommend setting `Object Ownership = BucketOwnerEnforced`
   for a permanent fix (ACLs disabled at the API layer).

