# Eval prompt: ok-clean-posture

Audit the following AWS Glue job configuration for security exposure. Emit
the standard VERDICT block (RESOURCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Resource: job ok-clean-posture
GlueVersion: 4.0
Role: arn:aws:iam::111111111111:role/glue-etl-ok-clean-posture
SecurityConfiguration: prod-glue-sec
Connections: {Connections: ["rds-pg-ok-clean-posture"]}

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

S3 source bucket (etl-source-ok-clean-posture):
  server-side-encryption-configuration:
    Rules:
      - ApplyServerSideEncryptionByDefault: {SSEAlgorithm: aws:kms, KMSMasterKeyID: alias/s3-cmk}

JDBC Connection (rds-pg-ok-clean-posture):
  ConnectionType: JDBC
  ConnectionProperties:
    JDBC_CONNECTION_URL: jdbc:postgresql://db.x.us-east-1.rds.amazonaws.com:5432/app
    USERNAME: etl_reader
    JDBC_ENFORCE_SSL: "true"

Execution role policy (glue-etl-ok-clean-posture):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Read",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::etl-source-ok-clean-posture",
        "arn:aws:s3:::etl-source-ok-clean-posture/*"
      ]
    },
    {
      "Sid": "GlueCatalogRW",
      "Effect": "Allow",
      "Action": ["glue:BatchCreatePartition", "glue:GetTable", "glue:GetDatabase"],
      "Resource": [
        "arn:aws:glue:us-east-1:111111111111:catalog",
        "arn:aws:glue:us-east-1:111111111111:database/default",
        "arn:aws:glue:us-east-1:111111111111:table/default/*"
      ]
    },
    {
      "Sid": "KMSDecrypt",
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/abc-123"
    }
  ]
}
```
