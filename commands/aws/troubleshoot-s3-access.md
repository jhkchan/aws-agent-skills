---
name: troubleshoot-s3-access
description: >-
  Slash command for the s3-access-troubleshooter skill. Diagnoses S3 403
  Access Denied on GetObject, PutObject, ListBucket, cross-account
  failures, presigned URL failures, and unexpected public access via a
  systematic six-symptom decision tree across the BPA hierarchy
  (account-level > bucket-level > ACL > bucket policy > IAM), KMS key
  policy, Object Ownership, VPC endpoint policy, CloudFront OAC, and
  Access Point policy. Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO |
  ESCALATE with the failing layer and statement.
skill: s3-access-troubleshooter
family: Storage
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
---

# /aws:troubleshoot-s3-access

Invoke the `s3-access-troubleshooter` skill to diagnose an S3 access
failure.

## When to use

- An S3 API call returns `403 AccessDenied` on `s3:GetObject`,
  `s3:PutObject`, or `s3:ListBucket`.
- Cross-account S3 access fails (caller account ≠ bucket account).
- A presigned URL returns 403 to a caller that "should" work.
- A bucket is unexpectedly publicly readable.
- An SSE-KMS object cannot be read by an otherwise-authorized principal.
- An upload fails with `AccessDenied` after a bucket policy SSE
  enforcement change.
- Object Lock retention is preventing overwrite/deletion.

## Invocation

```
/aws:troubleshoot-s3-access <description of the S3 AccessDenied scenario>
```

The skill will:

1. Identify the symptom category (GetObject / PutObject / ListBucket /
   cross-account / presigned URL / unexpected public).
2. Request the four mandatory context values: principal ARN, exact
   action, resource ARN (bucket + key), CloudTrail event.
3. Walk the seven-layer evaluation order: account-level BPA →
   bucket-level BPA → Object Ownership → ACL → bucket policy → IAM
   identity policy → KMS key policy (for SSE-KMS). VPC endpoint
   policy and CloudFront OAC are checked when applicable.
4. Apply the ARN-shape gate (object ARN vs bucket ARN) before any
   policy reading — this is the most common misdiagnosis.
5. Map the failure to the common root-cause catalog (10 patterns).
6. Verify the proposed fix with `aws iam simulate-principal-policy`
   before applying.
7. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <principal ARN> → <action> on <resource ARN>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <layer name> — <statement Sid or missing permission> —
<implicit or explicit deny>
EVIDENCE:
  - <layer>: <Allowed | Denied | Not evaluated> — <evidence line>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific policy edit + verification command>
```

## Pre-flight

The skill requires the CloudTrail event OR a policy simulator result to
distinguish implicit from explicit deny, AND the exact action + resource
ARN to apply the ARN-shape gate. If these are not available, the skill
emits `NEED_MORE_INFO` with the list of required inputs.

## References

- Skill: `skills/s3-access-troubleshooter/SKILL.md`
- Reference: `skills/s3-access-troubleshooter/references/bpa-hierarchy-and-truth-tables.md`
- Reference: `skills/s3-access-troubleshooter/references/kms-and-s3-cross-account-chain.md`
- AWS docs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html
