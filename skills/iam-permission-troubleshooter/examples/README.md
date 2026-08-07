# End-to-end usage scenario: iam-permission-troubleshooter

A walkthrough showing the skill diagnosing a cross-account KMS-encrypted
S3 AccessDenied incident, walking the full policy evaluation decision
tree across both accounts. This exercises Step 3 (same-account walk),
Step 7 (cross-account intersection rule), Step 8 (catalog #7 — KMS key
policy), and Step 10 (verdict decision).

## Input (user prompt)

> A Lambda function in account `111111111111` (role
> `arn:aws:iam::111111111111:role/app-lambda`) is getting `AccessDenied`
> on `s3:GetObject` against `arn:aws:s3:::prod-data/report.csv` in
> account `222222222222`. The bucket policy allows the Lambda role. The
> Lambda role identity policy has `s3:GetObject` on the bucket ARN and
> `kms:Decrypt` on the key. The bucket is encrypted with a customer-managed
> KMS key in account `222222222222`. The KMS key policy lists only
> account-`222222222222` roles.

## Skill output

```text
INCIDENT: arn:aws:sts::111111111111:assumed-role/app-lambda/... →
s3:GetObject on arn:aws:s3:::prod-data/report.csv
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: KMS key policy (resource-based on
arn:aws:kms:us-east-1:222222222222:key/abc123) — implicit deny — caller
role not granted kms:Decrypt
EVIDENCE:
  - SCP layer: Not evaluated (no SCPs in either account restrict S3/KMS)
  - S3 bucket policy (resource-based): Allowed — Principal includes the
    Lambda role ARN
  - Identity-based policy (Lambda role): Allowed — s3:GetObject on
    arn:aws:s3:::prod-data/* AND kms:Decrypt on the key ARN
  - Permissions boundary: Not present — skip
  - Session policy: Not present (direct Lambda invocation) — skip
  - KMS key policy (Layer 2 for KMS): NOT Allowed — key policy
    Principal.AWS lists account-222 roles only. Cross-account caller
    is not granted kms:Decrypt. The KMS Decrypt call is made BY S3 on
    behalf of the Lambda — S3 needs permission to use the key on the
    caller's behalf, which requires the caller role in the key policy.
ROOT_CAUSE_CATALOG: #7 (KMS key policy not granting decrypt to the
calling role)
REMEDIATION:
  1. Add to the KMS key policy in account 222222222222:
     {
       "Sid": "AllowDecryptCrossAccount",
       "Effect": "Allow",
       "Principal": { "AWS": "arn:aws:iam::111111111111:role/app-lambda" },
       "Action": "kms:Decrypt",
       "Resource": "*"
     }
  2. The Lambda role's identity-based policy already has kms:Decrypt
     on the key ARN (verified above), so the cross-account intersection
     rule is satisfied once the key policy is updated.
  3. Validate with:
     aws kms simulate-principal-policy \
       --policy-source-arn arn:aws:iam::111111111111:role/app-lambda \
       --action-names kms:Decrypt \
       --resource-arns arn:aws:kms:us-east-1:222222222222:key/abc123
  4. Monitor CloudTrail for Decrypt events in account 222222222222
     after the policy update — verify the Lambda is using the key as
     expected.
```

## What the skill caught that a generic assistant misses

1. **The six-layer evaluation walk.** A generic assistant often jumps to
   "add the permission to the Lambda role." The Lambda role already has
   the permission — the issue is in the KMS key policy, which is owned
   by a different account and is invisible from the Lambda's IAM console.

2. **Cross-account intersection rule.** A generic assistant may forget
   that cross-account access requires BOTH identity-based AND
   resource-based Allow. The skill explicitly verifies both sides before
   declaring the root cause.

3. **The S3 → KMS service-to-service chain.** The KMS Decrypt call is
   made by S3, not by the Lambda directly. A generic assistant may
   suggest adding `kms:Decrypt` to the Lambda role without realising
   the Lambda already has it — the missing piece is the key policy in
   the resource-owning account.

4. **The catalog match.** Mapping to catalog #7 gives the operator a
   named, known-good fix pattern instead of an ad-hoc suggestion.

## Slash-command invocation

```
/aws:troubleshoot-iam-permission
```

Or via the orchestrator:

```
/aws:pipeline
You: "Lambda in 1111 cannot read S3 object in 2222 — getting AccessDenied"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
iam-permission-troubleshooter]` and hands off to this skill for the
VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "Lambda cross-account AccessDenied on S3"
# [Phase: Troubleshoot | Skills routed: iam-permission-troubleshooter]
```

## Live-account diagnostic flow (optional, requires AWS CLI in both accounts)

When the operator has credentials for both accounts, the skill walks
the layers with live CLI calls:

```bash
# Account 111 (Lambda account):
aws iam list-attached-role-policies --role-name app-lambda --profile acct111
aws iam get-role --role-name app-lambda --query 'Role.PermissionsBoundary' --profile acct111

# Account 222 (resource account):
aws s3api get-bucket-policy --bucket prod-data --profile acct222
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
