# Eval prompt: cfn-drift-addition-import-bucket

Diagnose the following CloudFormation drift scenario. Walk the
diagnostic decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
RESOLUTION, REMEDIATION).

## Scenario

An operator discovers an S3 bucket `app-uploads-2026` in `us-east-1`
that was created via the AWS console. The bucket should be managed
by the existing `app-storage` CloudFormation stack, but the stack
template does not currently declare it.

## Known facts

- Bucket name: `app-uploads-2026` (region `us-east-1`).
- Current configuration:
  - Versioning: `Enabled`
  - Server-side encryption: SSE-KMS with the default S3 key
    (`alias/aws/s3`)
  - Lifecycle rule: transition `STANDARD_IA` objects to
    `GLACIER` after 90 days
  - Bucket policy: allows `s3:PutObject` from
    `arn:aws:iam::111122223333:role/app-uploader`
- The bucket currently holds 4 TB of existing objects — it must NOT
  be recreated.
- The `app-storage` stack (`StackStatus: CREATE_COMPLETE`) does not
  declare this bucket. `describe-stack-resources` does not list it.
- The operator wants to bring the bucket under stack management.

## Symptom

The operator needs to know how to bring the bucket under
CloudFormation management without losing the existing objects.
