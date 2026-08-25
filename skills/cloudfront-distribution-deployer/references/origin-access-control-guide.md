# Origin Access Control (OAC) and Origin Models Reference

Supplementary reference for the CloudFront Distribution Deployer skill.
Use when planning origins, configuring OAC on S3 buckets, migrating from
OAI to OAC, or designing multi-origin failover groups.

## OAC vs OAI (legacy)

| Dimension | Origin Access Control (OAC) | Origin Access Identity (OAI) — LEGACY |
|---|---|---|
| Introduced | 2022 | 2016 |
| SSE-KMS support | Yes (passes KMS Decrypt) | **No** — OAI cannot call KMS Decrypt |
| IPv6 support | Yes | No |
| Bucket policy principal | `Service: cloudfront.amazonaws.com` with `AWS:SourceArn` condition | `CanonicalUser` with CloudFront canonical ID |
| Signing protocol | sigv4 | Legacy |
| Signing behavior | `always`, `no-override`, `never` | Single mode |
| Recommendation | **Use for all new distributions** | Migrate to OAC; keep only for transition |

**Migration rule:** OAI is not "removed." It is deprecated in favor of
OAC. New distributions MUST use OAC. Existing distributions using OAI
should migrate — but the bucket policy MUST change simultaneously. The
OAI canonical-user grant becomes inert; the OAC service-principal
statement with `AWS:SourceArn` is what allows CloudFront access.

## OAC signing behavior

| Behavior | When to use |
|---|---|
| `always` | Private S3 origin. CloudFront signs every origin request. Default for static content. |
| `no-override` | Mixed auth: origin accepts its own `Authorization` header; CloudFront signs only when no header present. |
| `never` | Disabled. Equivalent to no OAC. Rare. |

## S3 bucket policy for OAC

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::prod-app-assets/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::<account>:distribution/<dist-id>"
      }
    }
  }]
}
```

**Critical:** The `AWS:SourceArn` condition prevents a different
distribution in the same account from accessing the bucket via its own
OAC. Without this condition, ANY distribution in the account with OAC
enabled can read the bucket. Always scope to the distribution ARN.

For write-through caching (CloudFront PUT/POST to S3), add `s3:PutObject`
to the action list and update the cache behavior to allow the verb.

## Custom origin (ALB, EC2, on-prem) configuration

```json
"CustomOriginConfig": {
  "HTTPPort": 80,
  "HTTPSPort": 443,
  "OriginProtocolPolicy": "https-only",
  "OriginSslProtocols": ["TLSv1.2"],
  "OriginReadTimeout": 30,
  "OriginKeepaliveTimeout": 5
}
```

**Origin custom headers (secrets / verification tokens):**
```json
"OriginCustomHeaders": [
  {"HeaderName": "X-Origin-Verify", "HeaderValue": "<shared-secret>"},
  {"HeaderName": "X-CloudFront-Request", "HeaderValue": "true"}
]
```

The ALB can validate `X-Origin-Verify` to ensure traffic originated from
CloudFront — not direct ALB access. Treat this header as a secret; rotate
periodically.

**Self-signed cert warning:** CloudFront does NOT trust self-signed
certificates. Use ACM (for ALB/EC2 with public DNS) or a public CA cert.
Private CA (AWS Private CA) is supported only via ACM with the private
certificate feature.

## Origin group failover

```json
"Origins": {
  "Quantity": 2,
  "Items": [
    {"Id": "primary-alb", "DomainName": "primary.example.com", "CustomOriginConfig": {...}},
    {"Id": "secondary-alb", "DomainName": "dr.example.com", "CustomOriginConfig": {...}}
  ]
},
"OriginGroups": {
  "Quantity": 1,
  "Items": [{
    "Id": "origin-group-ha",
    "Members": {"Quantity": 2, "Items": [
      {"OriginId": "primary-alb"},
      {"OriginId": "secondary-alb"}
    ]},
    "FailoverCriteria": {
      "StatusCodes": {"Quantity": 6, "Items": [403, 404, 500, 502, 503, 504]}
    }
  }]
}
```

**Active-passive:** primary serves all traffic; secondary activates on
matching failure status. The default cache behavior points to the origin
group ID (not individual origin IDs).

**Active-active:** NOT supported via origin group. Use Route 53 weighted
routing or CloudFront continuous deployment with traffic splitting.

**Failover criteria:** 5xx (origin failure) and 4xx (origin misconfig).
Common: 500, 502, 503, 504. Add 403 if the primary has IAM issues.
Avoid including 200 (would fail over on successful responses).

## VPC origins (2024-2025)

CloudFront VPC origins enable private-content delivery from VPC-attached
resources (ALB, NLB, EC2, ECS) without internet exposure. The VPC origin
is a CloudFront-managed ENI in your VPC subnets.

**Configuration:**
- The VPC origin ARN replaces the public DNS in the origin configuration.
- CloudFront routes traffic through the VPC ENI to the target resource.
- Security groups on the target resource must allow inbound from the
  CloudFront-managed ENI's security group.

**Use cases:**
- Internal-only applications needing global edge delivery.
- Compliance-bound workloads where the origin must not be internet-reachable.
- Latency-sensitive APIs served from a VPC-attached ECS service.

Verify that the VPC origin does not inadvertently expose resources that
were previously private — VPC origins change the network topology.

## Step 2: S3 bucket policy JSON for OAC (moved from SKILL.md)

**Update the S3 bucket policy to grant CloudFront access via OAC:**
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::prod-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::<account>:distribution/<dist-id>"
      }
    }
  }]
}
```
