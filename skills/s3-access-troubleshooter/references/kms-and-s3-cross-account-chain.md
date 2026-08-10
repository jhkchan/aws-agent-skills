# KMS and S3 Cross-Account Chain

Supplementary reference for the S3 Access Troubleshooter skill. Exhaustive
walkthrough of the S3 → KMS service-to-service chain, the
`aws:SourceAccount` / `aws:SourceArn` semantics that catch out
operators, and the cross-account write scenarios with
`BucketOwnerEnforced` Object Ownership.

## Why KMS is a separate gate

When an object is encrypted with a customer-managed KMS key (SSE-KMS),
two independent access decisions occur on `s3:GetObject`:

1. **S3 layer** — bucket policy + IAM identity policy must allow
   `s3:GetObject` on the object ARN.
2. **KMS layer** — KMS key policy + IAM identity policy must allow
   `kms:Decrypt` on the key ARN.

Each gate can independently deny. The error in both cases is
`AccessDenied` on `s3:GetObject` — there is no separate KMS error from
the S3 API. The only way to distinguish is CloudTrail:
- A KMS-layer deny shows up as a separate `kms:Decrypt` event with
  `errorCode: AccessDenied`.
- The S3-layer deny shows up as the `s3:GetObject` event with
  `errorCode: AccessDenied`.

For cross-account, both layers use the intersection rule:
identity-based AND resource-based must allow.

## The S3 → KMS service-to-service chain

When S3 reads an SSE-KMS object on behalf of a caller:

```
caller → s3:GetObject → S3 (s3.amazonaws.com) → kms:Decrypt → KMS
```

The `kms:Decrypt` call is made BY S3, not by the caller directly. This
is the source of subtle condition-key mismatches:

- `aws:SourceAccount` evaluates to the **S3 service's source account**,
  which is the **bucket's account**, NOT the caller's account.
- `aws:SourceArn` evaluates to the bucket's ARN (or the S3 access point
  ARN if accessed via AP).
- `aws:PrincipalArn` evaluates to the caller's role ARN.
- `kms:ViaService` evaluates to `s3.<region>.amazonaws.com`.

## The `aws:SourceAccount` trap

A common KMS key policy for S3 cross-account:

```json
{
  "Sid": "AllowS3ToDecryptForCaller",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111111111111:role/AppLambda" },
  "Action": "kms:Decrypt",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:SourceAccount": "111111111111"
    }
  }
}
```

**Operators intend:** "Only allow decrypt when the caller's account is
111111111111."

**Actual behavior:** The condition evaluates the S3 service call's
source account. If the bucket is in account `222222222222`, the source
account is `222222222222` — the condition fails, and the policy denies
the call.

**Fix:** Either remove the `aws:SourceAccount` condition, OR list the
bucket's account:

```json
"Condition": {
  "StringEquals": {
    "aws:SourceAccount": "222222222222"
  }
}
```

Or use `aws:SourceArn` to scope on the specific bucket:

```json
"Condition": {
  "StringEquals": {
    "aws:SourceArn": "arn:aws:s3:::prod-data"
  }
}
```

## Cross-account SSE-KMS GetObject — full layer audit

For a caller in account A reading an SSE-KMS object in bucket owned by
account B (key in account B):

```
1. Caller's identity policy (account A):
   - s3:GetObject on arn:aws:s3:::<bucket-b>/*   ← REQUIRED
   - kms:Decrypt on arn:aws:kms:<region>:<B>:key/<id>  ← REQUIRED

2. Bucket policy (account B):
   - Principal.AWS includes arn:aws:iam::<A>:role/<role>  ← REQUIRED
   - Action: s3:GetObject
   - Resource: arn:aws:s3:::<bucket-b>/*

3. KMS key policy (account B):
   - Principal.AWS includes arn:aws:iam::<A>:role/<role>  ← REQUIRED
   - Action: kms:Decrypt
   - (Optional) aws:SourceArn scoped to the bucket

4. Account-level BPA (account B):
   - Must NOT be in a state that blocks the caller. For authenticated
     IAM cross-account access, BPA does not directly block — but
     `RestrictPublicBuckets=True` restricts public policies. If the
     bucket policy uses `Principal: "*"` (instead of the specific role
     ARN), `RestrictPublicBuckets` restricts it to in-account only —
     cross-account callers are denied.

5. VPC endpoint policy (if applicable):
   - Must allow both s3:GetObject AND kms:Decrypt.
```

All five layers must allow. Any single deny propagates.

## Cross-account SSE-KMS PutObject — full layer audit

For a caller in account A writing an SSE-KMS object to a bucket in
account B (key in account B):

```
1. Caller's identity policy (account A):
   - s3:PutObject on arn:aws:s3:::<bucket-b>/*
   - kms:GenerateDataKey on the key ARN

2. Bucket policy (account B):
   - Principal.AWS includes arn:aws:iam::<A>:role/<role>
   - Action: s3:PutObject
   - (If BucketOwnerEnforced) Action: s3:PutObjectAcl on the bucket ARN
     (the bucket-owner-full-control ACL grant requires this)

3. KMS key policy (account B):
   - Principal.AWS includes arn:aws:iam::<A>:role/<role>
   - Action: kms:GenerateDataKey

4. Object Ownership (account B):
   - If BucketOwnerEnforced: caller MUST include
     `x-amz-acl: bucket-owner-full-control` in the PutObject request.
     The bucket policy must allow `s3:PutObjectAcl` (or
     `s3:PutObject` with the acl header).

5. Bucket policy SSE enforcement:
   - If the bucket policy denies PutObject without SSE-KMS, the caller
     must include `x-amz-server-side-encryption: aws:kms` and
     `x-amz-server-side-encryption-aws-kms-key-id: <key-arn>` in the
     request headers.
```

## Diagnostic flow for cross-account SSE-KMS failures

```bash
# Account A (caller): verify identity policy has both actions.
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<A>:role/<role> \
  --action-names s3:GetObject kms:Decrypt \
  --resource-arns arn:aws:s3:::<bucket>/<key> arn:aws:kms:<region>:<B>:key/<id> \
  --profile <profile-A>

# Account B (bucket + key): read both resource-based policies.
aws s3api get-bucket-policy --bucket <bucket> --profile <profile-B>
aws kms get-key-policy --key-id <key-id> --policy-name default --profile <profile-B>

# CloudTrail (account A or B): look for separate kms:Decrypt AccessDenied
# events alongside the s3:GetObject failure.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Decrypt \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s)
```

## Cross-account write with BucketOwnerEnforced

When the bucket's Object Ownership is `BucketOwnerEnforced` (default for
new buckets since April 2022), ACLs are disabled. Cross-account writers
must include `x-amz-acl: bucket-owner-full-control` in the PutObject
request, AND the bucket policy must allow it.

```bash
# Bucket owner checks ownership:
aws s3api get-bucket-ownership-controls --bucket <bucket> --profile <profile-B>
# Output: ObjectConfiguration.ObjectOwnership = BucketOwnerEnforced

# Caller's PutObject MUST include the acl header:
aws s3api put-object --bucket <bucket> --key <key> --body <file> \
  --acl bucket-owner-full-control \
  --server-side-encryption aws:kms \
  --ssekms-key-id arn:aws:kms:<region>:<B>:key/<id> \
  --profile <profile-A>
```

## Worked examples

### Example 1: Cross-account GetObject fails — KMS key policy missing caller

- Account A: caller `arn:aws:iam::111111111111:role/AppLambda`
- Account B: bucket `arn:aws:s3:::prod-data`, key
  `arn:aws:kms:us-east-1:222222222222:key/abc123`
- Identity policy (A): s3:GetObject on prod-data/* AND kms:Decrypt on
  the key. Verified Allowed.
- Bucket policy (B): Principal.AWS includes the role ARN. Verified
  Allowed.
- KMS key policy (B): Principal.AWS lists only account-222 roles. No
  grant to the cross-account caller.
- **Root cause:** KMS key policy missing caller.
- **Fix:** Add the caller to the key policy Principal.AWS.

### Example 2: Cross-account PutObject fails — SSE enforcement Deny

- Bucket policy (B) denies PutObject when
  `s3:x-amz-server-side-encryption != aws:kms`.
- Caller (A) uploads without the SSE header.
- **Root cause:** SSE enforcement Deny.
- **Fix:** Include `--server-side-encryption aws:kms` and
  `--ssekms-key-id <key-arn>` in the PutObject.

### Example 3: Cross-account PutObject fails — BucketOwnerEnforced

- Object Ownership (B): `BucketOwnerEnforced`.
- Caller (A) uploads without `x-amz-acl: bucket-owner-full-control`.
- **Root cause:** BucketOwnerEnforced rejects cross-account uploads
  without the bucket-owner-full-control ACL.
- **Fix:** Add `--acl bucket-owner-full-control` to the PutObject.

### Example 4: Cross-account GetObject fails — `aws:SourceAccount` trap

- KMS key policy (B): `aws:SourceAccount: 111111111111` (caller's
  account, intending "only allow caller's account").
- Bucket is in account 222222222222.
- **Root cause:** `aws:SourceAccount` evaluates the S3 service call's
  source account (bucket's account, 222222222222), not the caller's.
- **Fix:** Either change `aws:SourceAccount` to `222222222222`, or use
  `aws:SourceArn: arn:aws:s3:::prod-data`.

## Common KMS + S3 gotchas

- **`kms:Decrypt` requires both the identity policy AND the key policy
  (cross-account intersection).** Many operators think the key policy
  alone suffices. It does not.

- **`kms:GenerateDataKey` is required for PutObject on SSE-KMS buckets.**
  Operators often grant only `kms:Decrypt` and wonder why writes fail.

- **KMS grants vs key policy.** For ephemeral access, prefer
  `kms:CreateGrant` over editing the key policy. Grants are scoped to a
  specific grantee principal and can be revoked individually.

- **KMS key rotation does NOT change the key ARN.** A rotated key uses
  the same ARN — old policies continue to work. Do not assume "the key
  rotated so I need a new policy."

- **KMS aliases are NOT principals.** Key aliases (`alias/my-key`) are
  display names; policies must reference the key ARN
  (`arn:aws:kms:<region>:<acct>:key/<id>`), not the alias.

- **S3 server-side encryption with S3-managed keys (SSE-S3) does NOT
  have a separate KMS gate.** SSE-S3 uses AWS-managed keys that require
  no caller-side KMS permission. Only SSE-KMS (customer-managed) and
  SSE-KMS (AWS-managed but explicitly selected) involve the KMS layer.
