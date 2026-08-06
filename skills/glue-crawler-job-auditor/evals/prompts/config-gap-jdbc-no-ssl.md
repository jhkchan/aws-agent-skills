# Eval prompt: config-gap-jdbc-no-ssl

Audit the following AWS Glue job configuration for security exposure. Emit
the standard VERDICT block (RESOURCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Resource: job config-gap-jdbc-no-ssl
GlueVersion: 3.0
Role: arn:aws:iam::111111111111:role/glue-etl-config-gap-jdbc-no-ssl
SecurityConfiguration: (none)
Connections: {Connections: ["rds-pg-config-gap-jdbc-no-ssl"]}

DataCatalogEncryptionSettings:
  EncryptionAtRest:
    EncryptionMode: SSE-KMS
    SseAwsKmsKeyId: alias/glue-catalog
  ConnectionPasswordEncryption:
    ReturnConnectionPasswordEncrypted: true

S3 source bucket (etl-source-config-gap-jdbc-no-ssl):
  server-side-encryption-configuration:
    Rules:
      - ApplyServerSideEncryptionByDefault: {SSEAlgorithm: AES256}

JDBC Connection (rds-pg-config-gap-jdbc-no-ssl):
  ConnectionType: JDBC
  ConnectionProperties:
    JDBC_CONNECTION_URL: jdbc:postgresql://db.x.us-east-1.rds.amazonaws.com:5432/app
    USERNAME: etl_reader
    JDBC_ENFORCE_SSL: "false"

Execution role policy (glue-etl-config-gap-jdbc-no-ssl):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Read",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::etl-source-config-gap-jdbc-no-ssl",
        "arn:aws:s3:::etl-source-config-gap-jdbc-no-ssl/*"
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
