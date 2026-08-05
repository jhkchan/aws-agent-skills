# Eval prompt: no-encryption-catalog-disabled

Audit the following AWS Glue job configuration for security exposure. Emit
the standard VERDICT block (RESOURCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Resource: job no-encryption-catalog-disabled
GlueVersion: 3.0
Role: arn:aws:iam::111111111111:role/glue-etl-no-encryption-catalog-disabled
SecurityConfiguration: prod-glue-sec
Connections: none

DataCatalogEncryptionSettings:
  EncryptionAtRest:
    EncryptionMode: DISABLED
  ConnectionPasswordEncryption:
    ReturnConnectionPasswordEncrypted: true
    AwsKmsKeyId: alias/glue-catalog

SecurityConfiguration (prod-glue-sec):
  EncryptionConfiguration:
    CloudWatchEncryption: {CloudWatchEncryptionMode: SSE-KMS}
    S3Encryptions: [{EncryptionMode: SSE-KMS}]
    JobBookmarksEncryption: {JobBookmarksEncryptionMode: CSE-KMS}

S3 source bucket (etl-source-no-encryption-catalog-disabled):
  server-side-encryption-configuration:
    Rules:
      - ApplyServerSideEncryptionByDefault: {SSEAlgorithm: AES256}

Execution role policy (glue-etl-no-encryption-catalog-disabled):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Wildcard",
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    },
    {
      "Sid": "GlueCatalog",
      "Effect": "Allow",
      "Action": ["glue:BatchCreatePartition", "glue:GetTable", "glue:GetDatabase"],
      "Resource": "*"
    }
  ]
}
```
