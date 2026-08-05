# Eval prompt: config-gap-bookmarks-eol

Audit the following AWS Glue job configuration for security exposure. Emit
the standard VERDICT block (RESOURCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Resource: job config-gap-bookmarks-eol
GlueVersion: "0.9"
Role: arn:aws:iam::111111111111:role/glue-etl-config-gap-bookmarks-eol
SecurityConfiguration: legacy-glue-sec

DataCatalogEncryptionSettings:
  EncryptionAtRest:
    EncryptionMode: SSE-KMS
    SseAwsKmsKeyId: alias/glue-catalog
  ConnectionPasswordEncryption:
    ReturnConnectionPasswordEncrypted: true

SecurityConfiguration (legacy-glue-sec):
  EncryptionConfiguration:
    CloudWatchEncryption: {CloudWatchEncryptionMode: SSE-KMS}
    S3Encryptions: [{EncryptionMode: SSE-KMS}]
    JobBookmarksEncryption: {JobBookmarksEncryptionMode: DISABLED}

S3 source bucket (etl-source-config-gap-bookmarks-eol):
  server-side-encryption-configuration:
    Rules:
      - ApplyServerSideEncryptionByDefault: {SSEAlgorithm: AES256}

Execution role policy (glue-etl-config-gap-bookmarks-eol):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Read",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::etl-source-config-gap-bookmarks-eol",
        "arn:aws:s3:::etl-source-config-gap-bookmarks-eol/*"
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
