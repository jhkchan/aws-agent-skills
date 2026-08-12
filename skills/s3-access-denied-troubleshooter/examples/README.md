# Example usage: s3-access-denied-troubleshooter

A walkthrough showing the skill diagnosing an S3 Access Denied error
that appears to be a missing S3 permission but is actually a missing
KMS key policy grant, demonstrating the policy evaluation hierarchy,
the KMS-as-separate-gate concept, the evidence-backed
ROOT_CAUSE_IDENTIFIED verdict, and the targeted remediation.

## Input (user prompt)

> Our application role started getting Access Denied on S3 GetObject
> after we migrated to a customer-managed KMS key. The IAM policy and
> bucket policy both allow s3:GetObject. We've been debugging this
> as an S3 permissions issue for an hour. Help us find the root cause.

```text
Bucket: prod-data-bucket
Key: orders/2024/order-001.json
Caller: arn:aws:iam::111111111111:role/app-role
Action: s3:GetObject
Error: "Access Denied" (HTTP 403)

IAM policy (app-role):
  - Allow s3:GetObject on arn:aws:s3:::prod-data-bucket/*
  - Allow s3:ListBucket on arn:aws:s3:::prod-data-bucket

Bucket policy:
  - Allow s3:GetObject for principal
    arn:aws:iam::111111111111:role/app-role

Bucket encryption: SSE-KMS with
  arn:aws:kms:us-east-1:111111111111:key/abc-123
KMS key manager: CUSTOMER
KMS key state: Enabled
Caller kms:Decrypt on key abc-123: NOT PRESENT

CloudTrail errorMessage: "Access Denied" (no "explicit deny")
SCPs: none deny s3 or kms
Permission boundary: none
```

## Skill output

```text
TARGET: s3://prod-data-bucket/orders/2024/order-001.json
  caller: arn:aws:iam::111111111111:role/app-role
  action: s3:GetObject
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The S3 authorisation chain allows the request (IAM policy
  grants s3:GetObject, bucket policy grants s3:GetObject, no explicit
  Deny at any level). However, the objects are encrypted with SSE-KMS
  using a customer-managed CMK (arn:aws:kms:us-east-1:111111111111:
  key/abc-123). The KMS key policy is a SEPARATE gate from S3. The
  caller's IAM policy does not include kms:Decrypt on the key ARN.
  When S3 attempts to decrypt the object on behalf of the caller,
  the KMS service denies the kms:Decrypt call, and S3 returns
  "Access Denied" — the error message does not mention KMS.
ROOT_CAUSE: KMS_KEY_POLICY
EVIDENCE:
  - Symptom: application role gets "Access Denied" (HTTP 403) on
    every s3:GetObject call for SSE-KMS objects in prod-data-bucket.
    The error started after migrating from the default aws/s3 key
    to the customer-managed CMK.
  - Probe: aws iam simulate-principal-policy on app-role for
    s3:GetObject on prod-data-bucket/* returns "allowed".
  - Probe: aws s3api get-bucket-policy shows a statement allowing
    app-role to perform s3:GetObject. No Deny statements present.
  - Probe: aws iam simulate-principal-policy on app-role for
    kms:Decrypt on the key ARN returns "implicitDeny".
  - Passing: no SCP Deny for s3 or kms (Step 1); no bucket policy
    Deny (Step 4); no permission boundary on the role (Step 3);
    no VPC endpoint policy restricting S3 (Step 7).
REMEDIATION:
  1. Add kms:Decrypt on the key ARN to the app-role IAM policy:
     aws iam put-role-policy --role-name app-role \
       --policy-name kms-decrypt-prod \
       --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"kms:Decrypt","Resource":"arn:aws:kms:us-east-1:111111111111:key/abc-123"}]}'
  2. Verify with simulate-principal-policy for kms:Decrypt:
     aws iam simulate-principal-policy \
       --policy-source-arn arn:aws:iam::111111111111:role/app-role \
       --action-names kms:Decrypt \
       --resource-arns arn:aws:kms:us-east-1:111111111111:key/abc-123
  3. Re-test the application's s3:GetObject call.
CONFIRM: Before updating the role policy, emit and await:
  "CONFIRM: About to add kms:Decrypt on key abc-123 to role app-role.
   Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Walked the full policy evaluation hierarchy in order.** A generic
   assistant sees "Access Denied" and checks the IAM policy, finds
   s3:GetObject is allowed, and gets stuck. The skill walks SCPs,
   IAM, bucket policy, permission boundary, THEN checks KMS — finding
   the missing kms:Decrypt at the KMS gate.

2. **Identified KMS as a separate authorisation layer.** The error
   message says "Access Denied" with no mention of KMS. A generic
   assistant treats this as an S3 permissions issue. The skill
   recognises that SSE-KMS with a customer-managed key introduces a
   separate gate: the caller needs BOTH s3:GetObject AND kms:Decrypt.

3. **Correlated the symptom onset with the KMS migration.** The error
   started after migrating from the default aws/s3 key to the
   customer-managed CMK. The skill recognises this pattern: the
   default AWS-managed key requires no kms:Decrypt permission (S3
   decrypts transparently), but the customer-managed CMK requires
   explicit kms:Decrypt in the caller's IAM policy.

4. **Used simulate-principal-policy to prove the KMS gap.** The skill
   ran simulate-principal-policy for kms:Decrypt and got
   "implicitDeny" — positive evidence that the permission is missing,
   not a process of elimination.

5. **Recommended the targeted IAM policy fix.** The remediation adds
   kms:Decrypt on the specific key ARN, not kms:* on *. This follows
   least-privilege and avoids over-granting.

## Slash-command invocation

```
/aws:troubleshoot-s3-access-denied
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why app-role gets Access Denied on prod-data-bucket"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: s3-access-denied-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the access:

```bash
# Confirm the role now has kms:Decrypt
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/app-role \
  --action-names kms:Decrypt \
  --resource-arns arn:aws:kms:us-east-1:111111111111:key/abc-123 \
  --profile default --output json

# Confirm the application can read the object
aws s3api get-object --bucket prod-data-bucket \
  --key orders/2024/order-001.json /tmp/test-download \
  --profile default

# Monitor CloudTrail for any new AccessDenied events on the bucket
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -d '-30 minutes' +%s) --end-time $(date +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("AccessDenied"))'
```
