# Eval prompt: overpermissive-role-admin-wildcard

Audit the following AWS Glue job configuration for security exposure. Emit
the standard VERDICT block (RESOURCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Resource: job overpermissive-role-admin-wildcard
GlueVersion: 4.0
Role: arn:aws:iam::111111111111:role/glue-etl-overpermissive-role-admin-wildcard
SecurityConfiguration: prod-glue-sec

DataCatalogEncryptionSettings:
  EncryptionAtRest:
    EncryptionMode: SSE-KMS
    SseAwsKmsKeyId: alias/glue-catalog
  ConnectionPasswordEncryption:
    ReturnConnectionPasswordEncrypted: true
    AwsKmsKeyId: alias/glue-catalog

SecurityConfiguration (prod-glue-sec):
  EncryptionConfiguration:
    CloudWatchEncryption: {CloudWatchEncryptionMode: SSE-KMS}
    S3Encryptions: [{EncryptionMode: SSE-KMS}]
    JobBookmarksEncryption: {JobBookmarksEncryptionMode: CSE-KMS}

S3 source bucket (etl-source-overpermissive-role-admin-wildcard):
  server-side-encryption-configuration:
    Rules:
      - ApplyServerSideEncryptionByDefault: {SSEAlgorithm: aws:kms, KMSMasterKeyID: alias/s3-cmk}

Execution role policy (glue-etl-overpermissive-role-admin-wildcard):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AdminWildcard",
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    },
    {
      "Sid": "PassRoleAny",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*"
    }
  ]
}
```
