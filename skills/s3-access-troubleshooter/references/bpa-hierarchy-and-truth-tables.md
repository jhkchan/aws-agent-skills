# Block Public Access (BPA) Hierarchy and Truth Tables

Supplementary reference for the S3 Access Troubleshooter skill. Full BPA
scope interaction truth table (account-level vs bucket-level, per-setting
effective values), worked examples for each combination, and the
canonical precedence AWS uses when evaluating access.

## The BPA hierarchy

AWS evaluates S3 access against multiple layers in a fixed precedence.
The first matching rule wins:

```
1. Account-level BPA (s3control:GetPublicAccessBlock for the account)
       │ if any of the 4 settings blocks the request → DENY
       ▼
2. Bucket-level BPA (s3api:GetPublicAccessBlock for the bucket)
       │ if any of the 4 settings blocks the request → DENY
       ▼
3. Object Ownership (s3api:GetBucketOwnershipControls)
       │ if BucketOwnerEnforced → ACLs disabled (no-op ACL grants)
       ▼
4. ACL (s3api:GetBucketAcl / GetObjectAcl)
       │ if grant allows → ALLOW (subject to above)
       ▼
5. Bucket policy (s3api:GetBucketPolicy)
       │ if Allow matches → ALLOW (subject to above)
       │ if Deny matches → DENY
       ▼
6. IAM identity policy (caller's managed + inline policies)
       │ if Allow matches → ALLOW
       │ if no Allow → DENY (implicit)
       ▼
7. KMS key policy (for SSE-KMS objects, separate gate)
       │ if Allow matches for kms:Decrypt/GenerateDataKey → ALLOW
       │ if no Allow → DENY (independent of S3 layer decision)
       ▼ ALLOW
```

VPC endpoint policies and SCPs run in parallel as additional gates.

## The four BPA settings

| Setting | What it blocks |
|---|---|
| `BlockPublicAcls` | New PUT of public ACLs (bucket or object). Rejects the API call. |
| `IgnorePublicAcls` | Treats existing public ACLs as if absent (no-op). ACL still appears in `get-bucket-acl` but is silently ignored. |
| `BlockPublicPolicy` | New PUT of bucket policy with `Principal: "*"` and public-facing actions. Rejects the API call. |
| `RestrictPublicBuckets` | Restricts the blast radius of EXISTING public policies (and public ACLs when paired with `IgnorePublicAcls`): only the bucket owner account and authorized AWS service principals can access. |

## Account-level vs bucket-level interaction truth table

Each setting is independently settable at either scope. The EFFECTIVE
value is a logical OR — enabling a setting at EITHER scope is sufficient;
the more-restrictive scope wins.

| Setting | Bucket scope | Account scope | Effective value | Behavior |
|---|---|---|---|---|
| `BlockPublicAcls` | True | True | True | All public ACL PUTs rejected at both layers |
| `BlockPublicAcls` | True | False | True | Bucket-level rejects public ACL PUTs |
| `BlockPublicAcls` | False | True | True | Account-level rejects public ACL PUTs |
| `BlockPublicAcls` | False | False | False | Public ACL PUTs accepted |
| `IgnorePublicAcls` | True | True | True | All existing public ACLs treated as no-ops |
| `IgnorePublicAcls` | True | False | True | Bucket-level ignores existing ACLs |
| `IgnorePublicAcls` | False | True | True | Account-level ignores existing ACLs |
| `IgnorePublicAcls` | False | False | False | Existing ACLs honored |
| `BlockPublicPolicy` | True | True | True | All public-policy PUTs rejected |
| `BlockPublicPolicy` | True | False | True | Bucket-level rejects public-policy PUTs |
| `BlockPublicPolicy` | False | True | True | Account-level rejects public-policy PUTs |
| `BlockPublicPolicy` | False | False | False | Public-policy PUTs accepted |
| `RestrictPublicBuckets` | True | True | True | Public policies restricted to in-account + AWS service principals |
| `RestrictPublicBuckets` | True | False | True | Bucket-level restriction |
| `RestrictPublicBuckets` | False | True | True | Account-level restriction |
| `RestrictPublicBuckets` | False | False | False | No restriction on existing public policies |

## Practical implications

- **Account-level BPA fully on + bucket-level unset:** the bucket IS
  protected. This is the recommended production posture — enable once at
  account level, all current + future buckets inherit protection.

- **Bucket-level BPA fully on + account-level off:** the bucket IS
  protected. Account-level is preferred but bucket-level is sufficient
  for the specific bucket.

- **Partial BPA (3 of 4 settings) at one scope:** the missing setting
  leaves its specific vector open. NEVER claim "BPA is enabled" without
  verifying all 4 settings. E.g., enabling only `BlockPublicAcls` leaves
  existing public ACLs honored (because `IgnorePublicAcls` is False) and
  public policies accepted (because `BlockPublicPolicy` is False).

- **BPA does NOT block IAM identity policy grants.** A caller with
  `s3:GetObject` via an identity policy can read a private bucket
  regardless of BPA. BPA only blocks public access paths (ACLs and
  `Principal: "*"` policies).

- **`RestrictPublicBuckets` narrows but does not delete existing public
  policies.** A `Principal: "*"` policy with `RestrictPublicBuckets`
  True is restricted to in-account principals only. Out-of-account
  callers (including those with valid IAM credentials) are denied.

## Worked examples

### Example 1: Account BPA on, bucket BPA off, public bucket policy

- Account-level: all 4 settings True.
- Bucket-level: not configured (default off).
- Bucket policy: `Principal: "*"`, `Action: s3:GetObject`,
  `Resource: bucket/*`.
- Expected: in-account principals can read; out-of-account cannot.
  `RestrictPublicBuckets` (account-level True) restricts the public
  policy to in-account.

### Example 2: Account BPA off, bucket BPA on, legacy AllUsers ACL

- Account-level: off.
- Bucket-level: all 4 settings True.
- ACL: `AllUsers` READ.
- Expected: AllUsers ACL is silently ignored (`IgnorePublicAcls=True`).
  The bucket is effectively private.

### Example 3: Both BPA off, Object Ownership BucketOwnerEnforced, public ACL

- Account-level: off.
- Bucket-level: off.
- Object Ownership: `BucketOwnerEnforced`.
- ACL: `AllUsers` READ.
- Expected: ACL is silently ignored (`BucketOwnerEnforced` disables
  ACLs at the API layer). The bucket is effectively private.

### Example 4: Both BPA off, Object Ownership ObjectWriter, public ACL

- Account-level: off.
- Bucket-level: off.
- Object Ownership: `ObjectWriter` (legacy default).
- ACL: `AllUsers` READ.
- Expected: ACL is HONORED. The bucket is publicly readable. This is a
  real public access path — recommend enabling BPA.

## When to check each scope

1. Always start with account-level (covers all buckets).
2. Then check bucket-level (may be partially or fully set independently).
3. Then check Object Ownership (separate from BPA but interacts with ACL
   honoring).
4. Then check ACLs (only meaningful if Object Ownership permits them and
   BPA does not ignore them).
5. Then check bucket policy (the most common public path when BPA is
   off).
6. Then check IAM identity policy (the most common private-access
   misconfiguration).
7. For SSE-KMS, separately check the KMS key policy (independent gate).

## Diagnostic commands

```bash
# Account-level BPA (run once for the account):
aws s3control get-public-access-block --account-id <acct>

# Bucket-level BPA:
aws s3api get-public-access-block --bucket <name>

# Object Ownership:
aws s3api get-bucket-ownership-controls --bucket <name>

# ACLs (bucket + object):
aws s3api get-bucket-acl --bucket <name>
aws s3api get-object-acl --bucket <name> --key <key>

# Bucket policy:
aws s3api get-bucket-policy --bucket <name>

# Encryption (to determine if KMS is in play):
aws s3api get-bucket-encryption --bucket <name>

# KMS key policy (for SSE-KMS buckets):
aws kms get-key-policy --key-id <key-id> --policy-name default
```

## Common BPA troubleshooting pitfalls

- **"I disabled BPA and it still doesn't work."** BPA blocks public
  access only. If the failure is for an authenticated IAM principal,
  disabling BPA does not help. The cause is elsewhere (identity policy,
  KMS, bucket policy Deny, VPCe).

- **"My bucket policy allows Principal:* but it doesn't work."** Check
  BPA at both scopes. `RestrictPublicBuckets=True` restricts public
  policies to in-account principals only. Out-of-account callers are
  denied.

- **"The bucket is public even though I set BlockPublicAcls=True."**
  `BlockPublicAcls` only blocks new ACL PUTs. Existing ACLs are still
  honored unless `IgnorePublicAcls=True`. Verify all 4 settings.

- **"Account-level BPA was enabled without my knowledge."** AWS is
  rolling out account-level BPA enabled-by-default on new accounts (2024-
  2025). Verify with `aws s3control get-public-access-block` after any
  account refresh.
