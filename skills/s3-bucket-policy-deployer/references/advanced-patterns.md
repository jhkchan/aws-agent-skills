# Advanced Patterns — S3 Bucket Policy Deployer

Load-on-demand deep dives moved verbatim from SKILL.md: the
Mindset misconceptions, the three condition-key / ACL expert
heuristics, and recent AWS features.

## Mindset — the three misconceptions (full)

Three misconceptions dominate bucket-policy misdesign at
provisioning time:

- **"The bucket policy overrides the IAM policy."** It does not.
  S3 evaluates both. If the IAM policy denies access, no bucket
  policy Allow can override it. Conversely, a bucket policy Deny
  overrides an IAM Allow. The effective permission is the
  intersection of all applicable policies (IAM + bucket + access
  point).

- **"Principal: * with a Condition is safe."** It depends. A
  bucket policy with `Principal: *` + `Condition: aws:SourceVpce`
  restricts the network source but still allows ANY identity in
  the account (and potentially other accounts via VPC endpoints)
  to access the bucket. For identity-based restrictions, pair the
  condition with a specific principal.

- **"S3 ACLs and bucket policies are interchangeable."** They are
  not. ACLs are legacy, limited to 100 grants, cannot express
  conditions, and are ignored when Block Public Access is enabled.
  Always use bucket policies. ACLs should be disabled.

## Expert heuristic: the aws:SecureTransport condition operator

The #1 HTTPS-only policy bug is using the wrong condition operator.
A baseline model writes `StringNotEquals` instead of `Bool`.

```text
CORRECT (Bool operator):
  "Condition": {
    "Bool": { "aws:SecureTransport": "false" }
  }
  → Deny if the request was NOT over HTTPS (the key is a boolean)

WRONG (StringNotEquals):
  "Condition": {
    "StringNotEquals": { "aws:SecureTransport": "true" }
  }
  → Silently matches wrong values; aws:SecureTransport is "true"/"false"
    string but Bool is the canonical operator
```

**Why Bool is correct:** `aws:SecureTransport` is a boolean
condition key. The `Bool` operator evaluates it as a boolean
(`true`/`false`), which is the canonical and reliable form. Using
`StringNotEquals` works in some cases but is fragile — the key
value is case-sensitive and the string comparison can silently fail
on edge-case clients. **Always use `Bool` for `aws:SecureTransport`.**

**Complete HTTPS-only Deny statement:**
```json
{
  "Sid": "DenyInsecureTransport",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": [
    "arn:aws:s3:::my-bucket",
    "arn:aws:s3:::my-bucket/*"
  ],
  "Condition": {
    "Bool": { "aws:SecureTransport": "false" }
  }
}
```

**Key implication:** this single statement enforces HTTPS for ALL
S3 operations on the bucket. It is the production default and
should be in every bucket policy unless there is a specific reason
not to (e.g., a legacy HTTP-only client).

## Expert heuristic: aws:SourceVpce vs aws:SourceVpc vs aws:SourceIp

These three condition keys are routinely confused. Each controls a
different layer of network-source restriction.

| Key | What it checks | When it's populated | Common use |
|---|---|---|---|
| `aws:SourceVpce` | The VPC endpoint ID the request came through | Only when the request traverses a VPC endpoint | Restrict to a specific endpoint |
| `aws:SourceVpc` | The VPC ID the request came from | Only when the request traverses a VPC endpoint with private DNS | Restrict to a VPC |
| `aws:SourceIp` | The source IP address of the request | Always populated for direct requests; NOT populated for requests through some VPC endpoints | IP allow-listing |

**Critical gotcha:** `aws:SourceVpc` and `aws:SourceVpce` are ONLY
populated when the request goes through a VPC endpoint. Direct
internet requests do NOT have these keys set. If you use
`StringEquals` (positive match), internet requests are implicitly
denied. If you use `StringNotEquals` (negative match), internet
requests are implicitly ALLOWED — which is usually NOT what you
want.

**VPC-endpoint-only pattern (correct):**
```json
{
  "Sid": "DenyNotFromVpcEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": [
    "arn:aws:s3:::my-bucket",
    "arn:aws:s3:::my-bucket/*"
  ],
  "Condition": {
    "StringNotEquals": { "aws:SourceVpce": "vpce-0abc123def456" }
  }
}
```

This Deny blocks any request that does NOT come from the specified
VPC endpoint. Requests from the internet, other VPCs, or other
endpoints are denied.

**Key implication:** `aws:SourceIp` does NOT work for traffic
through a VPC endpoint (the source IP becomes the endpoint's
internal IP, not the client's). For VPC-based restrictions, use
`aws:SourceVpce` or `aws:SourceVpc`.

## Expert heuristic: policy vs ACL — policy always preferred

S3 has two access-control mechanisms: bucket/object policies and
ACLs. ACLs are legacy (pre-2015) and should not be used.

| Feature | Bucket Policy | ACL |
|---|---|---|
| Condition keys | Full support (aws:SecureTransport, aws:SourceVpce, etc.) | None |
| Cross-account | Native | Limited to canned grants |
| Size limit | 20 KB | 100 grants |
| Block Public Access interaction | Respected | **ACLs are ignored when BPA is enabled** |
| Recommendation | **Always use** | Legacy — disable |

**Production default:** disable ACLs entirely. Set the bucket
ownership control to `BucketOwnerEnforced` (S3 Object Ownership),
which disables ACLs and makes the bucket owner the owner of all
objects:

```bash
aws s3api put-bucket-ownership-controls \
  --bucket my-bucket \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]
```

With `BucketOwnerEnforced`, ACLs are disabled and all access control
flows through bucket policies and IAM. This is the AWS-recommended
default since 2022.

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **CloudFront OAC (2022-2023, refined 2024-2025):** Replaces the
  legacy OAI. Supports SSE-KMS, all HTTP methods, and CloudFront
  Functions. Use `Principal: { "Service": "cloudfront.amazonaws.com" }`
  with `AWS:SourceArn` condition.

- **S3 Object Ownership `BucketOwnerEnforced` (2022-2023):**
  Disables ACLs entirely. Makes the bucket owner the owner of all
  objects. The AWS-recommended default. ACLs are legacy.

- **S3 Access Points policy delegation (2023-2024 refinements):**
  Per-access-point policies evaluated alongside the bucket policy.
  Enables per-team policy management without bloating the bucket
  policy past the 20 KB limit.

- **S3 Multi-Region Access Point policies (2023-2024):** Separate
  policy document for MRAP. Failover controls added. MRAP policy
  does not replace bucket policies.

- **`aws:SourceVpc` / `aws:SourceVpce` for S3 (2023-2024):**
  Condition keys for VPC-source restriction. Only populated when
  the request traverses a VPC endpoint. Direct internet requests do
  NOT have these keys set.

- **S3 Batch Operations for policy enforcement (2024-2025):**
  Batch-replace ACLs with bucket-owner-full-control across millions
  of objects when migrating to `BucketOwnerEnforced`.
