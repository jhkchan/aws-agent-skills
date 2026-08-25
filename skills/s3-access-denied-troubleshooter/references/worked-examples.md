# Worked Examples — S3 Access Denied Troubleshooter

Secondary worked examples moved verbatim from SKILL.md. Loaded on demand.

## Worked example — Cross-account missing bucket policy

```text
TARGET: s3://shared-data-bucket/reports/daily.csv
  caller: arn:aws:iam::222222222222:role/cross-account-reader
  action: s3:GetObject
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The caller in account 222222222222 has an IAM policy allowing
  s3:GetObject on the bucket. However, the bucket is in account
  111111111111 and the bucket policy does not include a statement
  allowing account 222222222222. Cross-account S3 access requires
  BOTH the caller's IAM policy AND the bucket policy to explicitly
  allow (Step 4).
ROOT_CAUSE: CROSS_ACCOUNT_MISSING_BUCKET_POLICY
EVIDENCE:
  - Symptom: cross-account-reader role in 222222222222 gets
    AccessDenied on s3:GetObject.
  - Probe: aws iam simulate-principal-policy on cross-account-reader
    for s3:GetObject returns "allowed".
  - Probe: aws s3api get-bucket-policy on shared-data-bucket shows
    no statement for principal 222222222222.
  - Passing: no SCP Deny; no KMS encryption (SSE-S3); object
    ownership is BucketOwnerEnforced (not an ownership issue).
REMEDIATION:
  1. Add a bucket policy statement allowing account 222222222222:
     aws s3api put-bucket-policy --bucket shared-data-bucket \
       --policy '{"Version":"2012-10-17","Statement":[{"Sid":"CrossAccountRead","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::222222222222:root"},"Action":"s3:GetObject","Resource":"arn:aws:s3:::shared-data-bucket/reports/*"}]}'
  2. Verify from account 222222222222:
     aws s3api get-object --bucket shared-data-bucket \
       --key reports/daily.csv /tmp/test-download --profile caller
CONFIRM: Before updating the bucket policy, emit and await:
  "CONFIRM: About to add a cross-account bucket policy statement on
   shared-data-bucket for account 222222222222. Proceed? (yes/no)"
```

## Worked example — INSUFFICIENT_DATA

```text
TARGET: unknown (bucket name not provided)
VERDICT: INSUFFICIENT_DATA
REASON: The operator reported "S3 AccessDenied" but did not provide
  the bucket name, the specific S3 action, or the caller IAM principal.
  Without these, the diagnostic tree cannot be entered.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: bucket name, S3 action, caller principal ARN
REMEDIATION: Re-prompt for: (1) the bucket name and key prefix, (2)
  the exact S3 action and error message, and (3) the caller's IAM
  role ARN. For live diagnosis, also request the CloudTrail event.
```
