# Eval prompt: insufficient-context-need-more-info

Diagnose the following AccessDenied report. The user has provided only
a symptom — no CloudTrail event, no simulator output, no policy
documents. Emit the standard VERDICT block. If you cannot distinguish
implicit from explicit deny from the supplied context, emit
NEED_MORE_INFO and list the missing inputs.

## Scenario

A user reports "I am getting `AccessDenied` on `s3:GetObject` from my
Lambda function." They provide:

- Lambda role ARN: `arn:aws:iam::111111111111:role/app-lambda`
- Bucket name: `my-prod-bucket`

They have not run `simulate-principal-policy` and have not pulled the
CloudTrail event. No policy documents are attached.

## What they have NOT provided

- CloudTrail event (no `errorMessage` to distinguish implicit vs
  explicit deny).
- Policy simulator output (no `matchedStatements`).
- Identity-based policy contents.
- Resource-based (bucket) policy contents.
- Information about SCPs, permissions boundary, or session policy.
- Object ARN (object key) — only the bucket name.
- Encryption status of the object (KMS involvement unknown).
- Cross-account or same-account (bucket owning account unknown).
