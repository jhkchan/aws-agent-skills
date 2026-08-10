# Eval prompt: insufficient-context-need-more-info

Diagnose the following S3 AccessDenied report. Determine whether the
supplied context is sufficient to walk the diagnostic decision tree
definitively, and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION) — or
NEED_MORE_INFO with the specific missing inputs.

## Scenario

A user reports: "I am getting AccessDenied when uploading to my S3
bucket."

## Known facts

- The bucket name is provided.
- The user has not specified:
  - The calling principal ARN (IAM user? assumed role? federated?
    anonymous via presigned URL?).
  - The exact S3 action that was denied (PutObject? PutObjectAcl?
    CreateMultipartUpload?).
  - The object key being uploaded.
  - Whether the bucket has SSE-KMS encryption.
  - Any bucket policy or identity policy documents.
  - A CloudTrail event with `errorMessage`.
  - A `simulate-principal-policy` result.
  - Whether the caller is in the same account as the bucket or
    cross-account.

## Symptom

AccessDenied on upload to S3. No further context available.
