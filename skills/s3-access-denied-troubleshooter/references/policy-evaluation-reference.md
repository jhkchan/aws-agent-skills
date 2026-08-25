# S3 Policy Evaluation Reference Guide

Supplementary reference for the S3 Access Denied Troubleshooter skill.
Loaded on-demand when a diagnostic needs the full policy evaluation
hierarchy, explicit-deny rules, cross-account matrix, or condition key
semantics.

## Policy evaluation hierarchy (strict order)

S3 evaluates authorisation in the following order. A Deny at any level
blocks the request immediately. The evaluation stops at the first
Deny.

```
1. SCPs (org root → OU → account)
   ─ a Deny at any org level blocks before IAM is evaluated
   ─ an Allow SCP does NOT grant — it just removes the SCP barrier

2. IAM identity policy
   ─ the caller's managed + inline policies
   ─ for same-account: an Allow here is sufficient (bucket policy
     can be absent)
   ─ for cross-account: an Allow here is necessary but NOT sufficient

3. Permission boundary (if set on the role)
   ─ narrows effective permissions
   ─ effective = IAM policy AND boundary
   ─ if boundary denies, the request fails even if IAM allows

4. Session policy (if STS assumed role with --policy-arn or --policy)
   ─ ephemeral, applies only to this session
   ─ effective = IAM policy AND boundary AND session policy

5. Bucket policy
   ─ resource-based policy on the bucket
   ─ for same-account: if IAM OR bucket policy allows, access granted
   ─ for cross-account: BOTH IAM AND bucket policy must allow
   ─ a Deny here overrides any Allow from IAM

6. ACLs (if BucketOwnerEnforced is NOT set)
   ─ legacy per-object access control
   ─ evaluated only for object-level operations
   ─ if the object owner is not the bucket owner, the ACL on the
     object controls access independently of the bucket policy

7. KMS key policy (if object is SSE-KMS with customer-managed key)
   ─ SEPARATE gate from S3
   ─ the S3 service calls kms:Decrypt on behalf of the caller
   ─ caller needs kms:Decrypt in IAM AND the key policy must
     permit the caller's account

8. VPC endpoint policy (if traffic flows through an S3 endpoint)
   ─ additional gate for VPC-attached callers
   ─ a restrictive endpoint policy can deny even when all other
     layers allow

9. Block Public Access (account + bucket level)
   ─ pre-evaluation gate: checked before bucket policy
   ─ blocks public access patterns (Principal:* with public ACL/policy)

10. Object Lock (retention + legal hold)
    ─ post-evaluation gate: checked AFTER authorisation passes
    ─ blocks overwrite/delete regardless of permissions
    ─ COMPLIANCE mode: no bypass (not even root)
    ─ GOVERNANCE mode: bypass with s3:BypassGovernanceRetention
```

## Explicit deny vs implicit deny

| Type | Meaning | CloudTrail signal | simulate-principal-policy result |
|---|---|---|---|
| Explicit deny | A `Deny` statement matches somewhere in the hierarchy | `errorMessage` contains "explicit deny" | `explicitDeny` |
| Implicit deny | No `Allow` statement matches at the required level(s) | `errorMessage` is bare "Access Denied" | `implicitDeny` |

## Cross-account evaluation matrix

| Bucket in | Caller in | IAM allows | Bucket policy allows | Result |
|---|---|---|---|---|
| Account A | Account A | Yes | No | **Allow** (same-account: either allows) |
| Account A | Account A | Yes | Yes | **Allow** |
| Account A | Account A | No | Yes | **Allow** (same-account: either allows) |
| Account A | Account A | No | No | Deny |
| Account A | Account B | Yes | No | **Deny** (cross-account: both must allow) |
| Account A | Account B | Yes | Yes | **Allow** |
| Account A | Account B | No | Yes | **Deny** (cross-account: both must allow) |
| Account A | Account B | No | No | Deny |

The cross-account rule is the #1 source of cross-account S3
AccessDenied. Same-account access works with either policy alone;
cross-account requires mutual consent.

## Condition keys commonly used in S3 policies

| Condition key | Meaning | Use case |
|---|---|---|
| `aws:SourceIp` | Caller's source IP | Restrict access to corporate CIDR. NOT populated when a VPC Gateway endpoint is used. |
| `aws:SourceVpc` | The VPC ID of the caller | Use for VPC-attached workloads instead of SourceIp. |
| `aws:SourceVpce` | The VPC endpoint ID | Scope bucket access to a specific endpoint. |
| `aws:SourceAccount` | The account ID of the caller | Cross-service confused-deputy prevention. |
| `aws:SourceArn` | The ARN of the calling resource | Fine-grained service-to-service scoping. |
| `s3:prefix` | The key prefix in ListBucket | Restrict listing to specific prefixes. |
| `s3:max-keys` | Maximum keys returned | Limit ListBucket response size. |
| `s3:x-amz-acl` | The ACL header value | Require specific ACL on upload (e.g., `bucket-owner-full-control`). |
| `kms:ViaService` | The service making the KMS call | Scope KMS key usage to `s3.<region>.amazonaws.com`. |
| `kms:EncryptionContext:aws:s3:arn` | The bucket ARN in KMS encryption context | Restrict key usage to specific buckets. |
| `s3:DataAccessPointAccount` | The account that owns the access point | Scope access point policies. |
| `s3:DataAccessPointArn` | The access point ARN | Scope to a specific access point. |

## simulate-principal-policy semantics

The IAM Policy Simulator evaluates IAM identity policies and
permission boundaries but does NOT evaluate:
- Bucket policies (resource-based)
- VPC endpoint policies
- ACLs
- KMS key policies
- Block Public Access settings
- Object Lock retention

For a complete evaluation, always cross-reference `simulate-principal-policy`
results with the actual CloudTrail event for the denied call.

## x-amz-expected-bucket-owner header

When `BucketOwnerEnforced` is set (default for new buckets since April
2023), S3 requires the `x-amz-expected-bucket-owner` header on
requests from cross-account callers. The header value must match the
bucket owner's account ID. A mismatch produces AccessDenied.

Most AWS SDKs support this via a request parameter:

```python
# Boto3 example
s3.get_object(
    Bucket='shared-bucket',
    Key='file.txt',
    ExpectedBucketOwner='111111111111'  # bucket owner account
)
```

## Deep reference: S3 authorisation evaluation model

### Policy evaluation hierarchy (strict order)

```
1. SCPs (org root → OU → account)     — a Deny at any level blocks
2. IAM identity policy                  — the caller's effective permissions
3. Permission boundary (if set)         — narrows effective permissions
4. Session policy (if STS assumed)      — further narrows for this session
5. Bucket policy                        — resource-based policy
6. ACLs (if BucketOwnerEnforced=false)  — legacy per-object access
7. KMS key policy (if SSE-KMS)         — separate gate for decrypt
8. VPC endpoint policy (if applicable)  — additional gate for VPC traffic
9. Block Public Access                  — pre-evaluation gate for public access
10. Object Lock                         — post-evaluation gate for write/delete
```

### Explicit deny vs implicit deny

| Type | Meaning | CloudTrail signal |
|---|---|---|
| Explicit deny | A `Deny` statement exists somewhere | `errorMessage` contains "explicit deny" |
| Implicit deny | No `Allow` statement matches | `errorMessage` is bare "Access Denied" |

### Cross-account evaluation matrix

| Bucket in | Caller in | IAM policy allows | Bucket policy allows | Result |
|---|---|---|---|---|
| Account A | Account A | Yes | No | Allow (same-account: either allows) |
| Account A | Account A | Yes | Yes | Allow |
| Account A | Account A | No | Yes | Allow (same-account: either allows) |
| Account A | Account B | Yes | No | Deny (cross-account: both must allow) |
| Account A | Account B | Yes | Yes | Allow |
| Account A | Account B | No | Yes | Deny (cross-account: both must allow) |
