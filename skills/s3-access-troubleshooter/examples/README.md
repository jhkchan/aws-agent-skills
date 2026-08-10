# End-to-end usage scenario: s3-access-troubleshooter

A walkthrough showing the skill diagnosing a cross-account KMS-encrypted
S3 GetObject incident, walking the full diagnostic decision tree across
both accounts. This exercises Step 1 (GetObject path), Step 4
(cross-account intersection rule), the BPA hierarchy check, and the
S3 → KMS service-to-service chain.

## Input (user prompt)

> A Lambda function in account `111111111111` (role
> `arn:aws:iam::111111111111:role/app-lambda`) is getting `AccessDenied`
> on `s3:GetObject` against `arn:aws:s3:::prod-data/report.csv` in
> account `222222222222`. The bucket policy in account 2222 allows the
> Lambda role. The Lambda role identity policy has `s3:GetObject` on
> `arn:aws:s3:::prod-data/*` AND `kms:Decrypt` on
> `arn:aws:kms:us-east-1:222222222222:key/abc123`. The bucket is
> encrypted with that customer-managed KMS key. The KMS key policy in
> account 2222 lists only account-222 roles in Principal.

## Skill output

```text
INCIDENT: arn:aws:sts::111111111111:assumed-role/app-lambda/... →
s3:GetObject on arn:aws:s3:::prod-data/report.csv
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: KMS key policy (resource-based on
arn:aws:kms:us-east-1:222222222222:key/abc123) — implicit deny — caller
role not granted kms:Decrypt. The S3 layer allows the request (identity
policy has s3:GetObject on the object ARN; bucket policy includes the
caller's role ARN). The KMS Decrypt call is made BY S3 on the caller's
behalf and is denied at the key policy because the caller's role is not
in Principal.AWS.
EVIDENCE:
  - Identity-based policy (caller, account 111111111111): Allowed —
    s3:GetObject on arn:aws:s3:::prod-data/* (object ARN, correct shape)
    AND kms:Decrypt on the key ARN (verified)
  - S3 bucket policy (account 222222222222): Allowed — Principal.AWS
    includes arn:aws:iam::111111111111:role/app-lambda, Action
    s3:GetObject, Resource arn:aws:s3:::prod-data/*
  - Account-level BPA (account 222222222222): not blocking (caller is
    authenticated IAM, not public)
  - Bucket-level BPA: not blocking (same reason)
  - Object Ownership: BucketOwnerEnforced (does not affect reads)
  - VPC endpoint policy: not in path (caller is Lambda not in VPC)
  - KMS key policy (account 222222222222): DENIED — Principal.AWS lists
    only account-222 roles; no grant for
    arn:aws:iam::111111111111:role/app-lambda. The kms:Decrypt call
    made by S3 on behalf of the caller fails here.
ROOT_CAUSE_CATALOG: #2 (KMS key policy missing cross-account caller)
REMEDIATION:
  1. Add to the KMS key policy in account 222222222222:
     {
       "Sid": "AllowCrossAccountDecrypt",
       "Effect": "Allow",
       "Principal": { "AWS": "arn:aws:iam::111111111111:role/app-lambda" },
       "Action": "kms:Decrypt",
       "Resource": "*"
     }
  2. The Lambda role's identity policy already has kms:Decrypt on the
     key ARN (verified), so the cross-account intersection rule at KMS
     is satisfied once the key policy is updated.
  3. Validate with:
     aws iam simulate-principal-policy \
       --policy-source-arn arn:aws:iam::111111111111:role/app-lambda \
       --action-names kms:Decrypt \
       --resource-arns arn:aws:kms:us-east-1:222222222222:key/abc123
  4. Monitor CloudTrail for kms:Decrypt events in account 222222222222
     after the policy update — verify the Lambda is using the key as
     expected.
```

## What the skill caught that a generic assistant misses

1. **The six-layer evaluation walk.** A generic assistant often jumps to
   "add the permission to the Lambda role." The Lambda role already has
   the permission — the issue is in the KMS key policy, which is owned
   by a different account and is invisible from the Lambda's IAM console.

2. **The ARN-shape gate.** The skill verified `s3:GetObject` is on the
   OBJECT ARN (`prod-data/*`), not the bucket ARN. A generic assistant
   may have suggested "use the bucket ARN" — which would not have
   helped.

3. **The cross-account intersection rule.** The skill verified BOTH
   sides (identity in caller account, bucket policy in resource account)
   before declaring the root cause. Cross-account access requires BOTH
   to allow.

4. **The S3 → KMS service-to-service chain.** The KMS Decrypt call is
   made by S3, not by the Lambda directly. A generic assistant may have
   suggested adding `kms:Decrypt` to the Lambda role without realising
   the Lambda already has it — the missing piece is the key policy in
   the resource-owning account.

5. **The catalog match.** Mapping to catalog #2 gives the operator a
   named, known-good fix pattern instead of an ad-hoc suggestion.

## Slash-command invocation

```
/aws:troubleshoot-s3-access
```

Or via the orchestrator:

```
/aws:pipeline
You: "Lambda in 1111 cannot read S3 object in 2222 — getting AccessDenied"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
s3-access-troubleshooter]` and hands off to this skill for the VERDICT.

## Live-account diagnostic flow (optional, requires AWS CLI in both accounts)

When the operator has credentials for both accounts, the skill walks the
layers with live CLI calls:

```bash
# Account 111 (Lambda account):
aws iam list-attached-role-policies --role-name app-lambda --profile acct111
aws iam get-role --role-name app-lambda --query 'Role.PermissionsBoundary' --profile acct111

# Account 222 (resource account):
aws s3api get-bucket-policy --bucket prod-data --profile acct222
aws s3api get-bucket-encryption --bucket prod-data --profile acct222
aws kms get-key-policy --key-id abc123 --policy-name default --profile acct222

# Simulate the Lambda role against the exact action and resource:
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/app-lambda \
  --action-names s3:GetObject kms:Decrypt \
  --resource-arns arn:aws:s3:::prod-data/report.csv \
                 arn:aws:kms:us-east-1:222222222222:key/abc123 \
  --profile acct111 --output json
```

If `simulate-principal-policy` returns `implicitDeny` for `kms:Decrypt`,
the diagnosis is confirmed without ever reading the key policy from
account 222 — the Lambda's identity policy has the action, so the deny
must be on the key-policy side.
