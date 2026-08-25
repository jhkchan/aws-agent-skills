# Policy Patterns Deep Dive — S3 Bucket Policy Deployer

Detailed reference for common S3 bucket policy patterns with
copy-pasteable JSON, condition key semantics, and gotchas. Loaded
on-demand when the operator needs to reason about which pattern
applies.

## Pattern comparison

| Pattern | Condition key | Operator | Effect | Use case |
|---|---|---|---|---|
| HTTPS-only | `aws:SecureTransport` | `Bool` | Deny | Enforce TLS |
| Cross-account | `aws:ExternalId` | `StringEquals` | Allow | Third-party access |
| VPC-endpoint-only | `aws:SourceVpce` | `StringNotEquals` | Deny | Private network |
| VPC-scoped | `aws:SourceVpc` | `StringNotEquals` | Deny | VPC restriction |
| IP-allow-list | `aws:SourceIp` | `NotIpAddress` | Deny | IP restriction |
| CloudFront OAC | `AWS:SourceArn` | `StringEquals` | Allow | CDN origin |
| Service access | `s3:x-amz-acl` | `StringEquals` | Allow | Logging, Lambda |
| MFA-required | `aws:MultiFactorAuthPresent` | `Bool` | Deny | Delete protection |

## HTTPS-only (aws:SecureTransport)

**Condition operator: `Bool`** (NOT `StringNotEquals`).

```json
{
  "Sid": "DenyInsecureTransport",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
  "Condition": { "Bool": { "aws:SecureTransport": "false" } }
}
```

**Why Bool:** `aws:SecureTransport` is a boolean key. `Bool`
evaluates it canonically (`true`/`false`). `StringNotEquals` is
fragile — the string comparison can silently fail on edge-case
clients that send non-standard header values.

**Important:** this Deny blocks ALL non-HTTPS traffic. Some legacy
tools or internal services may use HTTP — test before applying in
production.

## Cross-account with ExternalId

```json
{
  "Sid": "AllowCrossAccountWithExternalId",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::998877665544:role/PartnerRole" },
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::my-bucket",
    "arn:aws:s3:::my-bucket/shared/*"
  ],
  "Condition": {
    "StringEquals": { "aws:ExternalId": "unique-external-id-12345" }
  }
}
```

**The ExternalId is set by the assuming role** in the STS
`AssumeRole` call. The bucket policy checks it to prevent the
confused-deputy problem. The foreign account's role trust policy
must also enforce the ExternalId.

**Scope rules:**
- Use a specific role ARN, not `:root` (which delegates to the
  entire account).
- Scope `Resource` to specific prefixes (`shared/*`) rather than
  `/*` when the partner only needs a subset.
- Both the bucket policy AND the foreign role's IAM policy must
  Allow — S3 evaluates both.

## VPC-endpoint-only (aws:SourceVpce)

```json
{
  "Sid": "DenyNotFromVpcEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
  "Condition": {
    "StringNotEquals": { "aws:SourceVpce": "vpce-0abc123def456" }
  }
}
```

**Key semantics:**
- `aws:SourceVpce` is ONLY populated when the request traverses a
  VPC endpoint. Direct internet requests do NOT have this key.
- `StringNotEquals` (Deny) blocks any request where the key does
  not match the specified endpoint ID — including all internet
  traffic.
- A wrong endpoint ID silently blocks ALL access. Verify before
  applying.

**Multiple endpoints:** to allow traffic from multiple endpoints,
use `StringNotEqualsIfExists`:
```json
"Condition": {
  "StringNotEqualsIfExists": {
    "aws:SourceVpce": ["vpce-0abc123", "vpce-0def456"]
  }
}
```

## VPC-scoped (aws:SourceVpc)

```json
{
  "Sid": "DenyNotFromVpc",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
  "Condition": {
    "StringNotEquals": { "aws:SourceVpc": "vpc-0abc123def456" }
  }
}
```

**Key difference from SourceVpce:** `aws:SourceVpc` identifies the
VPC, not the specific endpoint. It allows traffic from ANY endpoint
in the specified VPC. Use this when you want VPC-scoped access
without pinning to a specific endpoint.

**Same gotcha:** only populated for requests through VPC endpoints.
Direct internet requests do NOT have `aws:SourceVpc` set.

## IP-allow-list (aws:SourceIp)

```json
{
  "Sid": "DenyNotFromAllowedIPs",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
  "Condition": {
    "NotIpAddress": { "aws:SourceIp": ["10.0.0.0/8", "203.0.113.0/24"] }
  }
}
```

**Key limitation:** `aws:SourceIp` does NOT work for requests
through a VPC endpoint or NAT gateway. The source IP becomes the
endpoint's or NAT's internal IP, not the client's. For VPC-based
restrictions, use `aws:SourceVpce` or `aws:SourceVpc`.

## CloudFront OAC

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontOAC",
    "Effect": "Allow",
    "Principal": { "Service": "cloudfront.amazonaws.com" },
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/E123ABCDEF456"
      }
    }
  }]
}
```

**OAC vs OAI:**
| Feature | OAC (current) | OAI (legacy) |
|---|---|---|
| SSE-KMS support | Yes | No |
| All HTTP methods | Yes | Limited |
| Principal | `cloudfront.amazonaws.com` service | Canonical user ID |
| Condition | `AWS:SourceArn` | None |
| Migration | Recommended | Deprecated |

**Key rule:** always include the `AWS:SourceArn` condition. Without
it, ANY CloudFront distribution in the account can access the
bucket.

## Service access with s3:x-amz-acl

```json
{
  "Sid": "AllowLoggingServiceWithACL",
  "Effect": "Allow",
  "Principal": { "Service": "logging.amazonaws.com" },
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::my-bucket/logs/*",
  "Condition": {
    "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control" }
  }
}
```

**Why the ACL condition:** when an AWS service writes to a
cross-account bucket, the writing account owns the objects by
default. The `s3:x-amz-acl: bucket-owner-full-control` condition
forces the writer to grant the bucket owner full control — so the
bucket account can read the objects.

**This is NOT the same as using S3 ACLs for access control.** The
`s3:x-amz-acl` condition key is a bucket-policy condition, not an
ACL. The policy is still the access-control mechanism.

## MFA-required for deletes

```json
{
  "Sid": "DenyDeleteWithoutMFA",
  "Effect": "Deny",
  "Principal": { "AWS": "arn:aws:iam::123456789012:role/DataAdmin" },
  "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
  "Resource": "arn:aws:s3:::my-bucket/*",
  "Condition": {
    "Bool": { "aws:MultiFactorAuthPresent": "false" }
  }
}
```

Requires the caller to authenticate with MFA before deleting
objects. Useful for production data buckets.

## Combining patterns

Multiple statements can be combined in a single policy. The
effective permission is the intersection of all statements — any
Deny overrides any Allow.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "DenyInsecureTransport", ... },
    { "Sid": "DenyNotFromVpcEndpoint", ... },
    { "Sid": "AllowCrossAccountWithExternalId", ... }
  ]
}
```

**Order does not matter** — S3 evaluates all statements. A Deny in
statement 1 overrides an Allow in statement 3 regardless of order.

## Policy size mitigation

When a policy approaches the 20 KB limit:

1. **Use Access Points** to split per-team policies into separate AP
   policy documents.
2. **Use wildcard prefixes** — `shared/*` instead of listing each
   prefix.
3. **Merge similar statements** — combine actions and resources
   into arrays rather than separate statements.
4. **Move identity-based rules to IAM** — if the policy grants
   access to specific roles, the same access can be an IAM policy
   attached to the role (no bucket policy needed for same-account
   access).

## Canonical bucket-policy structure example (Step 1)

Every bucket policy is a JSON document with a `Version` and a
`Statement` array. Each statement has four core elements.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": " descriptive-label",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/MyRole" },
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {
        "Bool": { "aws:SecureTransport": "true" }
      }
    }
  ]
}
```
