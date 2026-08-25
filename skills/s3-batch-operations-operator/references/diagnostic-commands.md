# Diagnostic Commands — S3 Batch Operations Operator

Load-on-demand pre-flight command listings moved verbatim from
SKILL.md.

## Live-account pre-flight (skip if offline plan audit)

1. `aws s3api head-object --bucket <manifest-bucket> --key <manifest-
   key>` — confirm manifest exists and role can read it. For S3
   inventory manifests, verify both `manifest.json` and
   `manifest.checksum` are present.
2. `aws s3api get-bucket-location --bucket <report-bucket>` — confirm
   the report bucket is in the same Region as the planned job.
3. `aws s3api get-bucket-versioning --bucket <target-bucket>` — capture
   versioning state (relevant for copy-with-version and object-lock
   operations).
4. `aws iam list-attached-role-policies --role-name <role>` and
   `aws iam list-role-policies --role-name <role>` — verify the role's
   permission chain.
5. `aws kms describe-key --key-id <source-key>` and
   `aws kms get-key-policy --key-id <source-key> --policy-name default`
   — confirm source KMS key `Enabled` and grants the role.
6. For copy/re-encrypt: repeat #5 for the destination KMS key.
7. For invoke operations: `aws lambda get-policy --function-name
   <lambda>` — confirm `batchoperations.amazonaws.com` principal with
   `lambda:InvokeFunction` scoped to the job role.
8. For existing job diagnosis: `aws s3control describe-job --account-id
   <account> --job-id <id>` — capture `Status`, `ProgressSummary`,
   `FailureCodes` distribution.
