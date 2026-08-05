# Eval prompt: no-encryption-s3-source-unencrypted

Audit the following AWS Glue job configuration for security exposure. Emit
the standard VERDICT block (RESOURCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Resource: job no-encryption-s3-source-unencrypted
GlueVersion: 3.0
Role: arn:aws:iam::111111111111:role/glue-etl-no-encryption-s3-source-unencrypted
SecurityConfiguration: prod-glue-sec

DataCatalogEncryptionSettings:
  EncryptionAtRest:
    EncryptionMode: SSE-KMS
    SseAwsKmsKeyId: alias/glue-catalog
  ConnectionPasswordEncryption:
    ReturnConnectionPasswordEncrypted: true

SecurityConfiguration (prod-glue-sec):
  EncryptionConfiguration:
    CloudWatchEncryption: {CloudWatchEncryptionMode: SSE-KMS}
    S3Encryptions: [{EncryptionMode: SSE-KMS}]
    JobBookmarksEncryption: {JobBookmarksEncryptionMode: CSE-KMS}

S3 source bucket (etl-source-no-encryption-s3-source-unencrypted):
  server-side-encryption-configuration: (none — no SSE configured)

Execution role policy (glue-etl-no-encryption-s3-source-unencrypted):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Read",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::etl-source-no-encryption-s3-source-unencrypted",
        "arn:aws:s3:::etl-source-no-encryption-s3-source-unencrypted/*"
      ]
    },
    {
      "Sid": "GlueCatalogRW",
      "Effect": "Allow",
      "Action": ["glue:BatchCreatePartition", "glue:GetTable", "glue:GetDatabase"],
      "Resource": "arn:aws:glue:us-east-1:111111111111:catalog"
    }
  ]
}
```
