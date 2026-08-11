# Connection Tuning and Extra Connection Attributes — DMS Endpoint Deployer

Deep reference on DMS extra connection attributes per engine, SSL mode
selection, Secrets Manager integration, and connection troubleshooting.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Extra connection attributes reference

Extra connection attributes use a semicolon-delimited `key=value` syntax.
They are engine-specific. Invalid attributes may be silently ignored by
some engines.

### PostgreSQL source attributes

| Attribute | Default | Description |
|---|---|---|
| PluginName | test_decoding | Logical decoding plugin (pglogical recommended) |
| slotName | (auto) | Replication slot name (unique per task) |
| secretsManagerSecretId | (none) | Secrets Manager secret ARN for credentials |
| executeTimeout | 60 | Query timeout in seconds |
| mapBooleanAsBoolean | false | Map PostgreSQL boolean to MySQL boolean |

### Oracle source attributes

| Attribute | Default | Description |
|---|---|---|
| useLogminerReader | Y | Use LogMiner (Y) or Binary Reader (N) for CDC |
| AdditionalArchivedLogDestId | (none) | Archived log destination ID for Binary Reader |
| ExtraArchivedLogDestIds | (none) | Additional archived log destinations |
| EnableHomogenousTablespace | false | Map tablespaces with same names across source/target |
| numberDataTypeAdditionalInfo | (none) | Precision/scale handling for NUMBER type |

### MySQL source attributes

| Attribute | Default | Description |
|---|---|---|
| eventsPollInterval | 5 | Seconds between binary log reads |
| initstmt | (none) | SQL statements executed on connection |
| cleanSrcMetadataOnRestart | false | Clean source metadata on task restart |
| MaxLongStringLength | 19KB | Max length for LONG VARCHAR columns |

### MongoDB source attributes

| Attribute | Default | Description |
|---|---|---|
| NestingLevel | NONE | Document nesting level (ONE or NONE) |
| ExtractDocId | false | Extract document _id field |
| DocsToInvestigate | 1000 | Number of documents to sample for schema |
| authSource | admin | Authentication database |

### S3 target attributes

| Attribute | Default | Description |
|---|---|---|
| DataFormat | csv | Output format (csv or parquet) |
| CompressionType | NONE | Compression (NONE, GZIP, SNAPPY, ZSTD) |
| EncodingType | rle-dictionary | Parquet encoding type |
| AddColumnName | false | Include column names in output header |
| MaxFileSize | 1GB | Max file size before rotation |
| CsvRowDelimiter | \n | CSV row delimiter |
| CsvDelimiter | , | CSV column delimiter |

### Redshift target attributes

| Attribute | Default | Description |
|---|---|---|
| AcceptAnyDate | false | Accept any date format without validation |
| AfterConnectScript | (none) | SQL to execute after connection |
| MaxFileSize | 1GB | Max file size for S3 staging |
| TruncateCols | false | Truncate column data to fit target type |

### Kinesis target attributes

| Attribute | Default | Description |
|---|---|---|
| MessageFormat | json | Output format (json or json-unformatted) |
| ServiceAccessRoleArn | (required) | IAM role for Kinesis access |
| IncludeTransactionDetails | false | Include transaction metadata in messages |

## SSL mode selection

```text
SSL mode decision tree:
  ├── Dev/test, no sensitive data → none (or require)
  ├── Production, internal network → require (encryption without verification)
  ├── Production, any network → verify-ca (encryption + CA verification)
  └── Compliance requirement (HIPAA/PCI/SOC2) → verify-full (encryption + CA + hostname)
```

### Importing certificates

```bash
# Import a PEM certificate
aws dms import-certificate \
  --certificate-identifier "prod-ca-cert" \
  --certificate-pem "fileb://prod-ca.pem" \
  --region us-east-1

# Import a PKCS12 certificate
aws dms import-certificate \
  --certificate-identifier "prod-ca-cert" \
  --certificate-pkcs12 "fileb://prod-ca.p12" \
  --certificate-password '<cert_password>' \
  --region us-east-1
```

### Certificate management

```bash
# List certificates
aws dms describe-certificates --region us-east-1

# Delete an expired certificate
aws dms delete-certificate \
  --certificate-arn "arn:aws:dms:us-east-1:123456789012:cert:prod-ca-cert" \
  --region us-east-1
```

DMS does NOT auto-rotate certificates. Monitor expiration and re-import
before expiry to avoid SSL failures.

## Secrets Manager integration

### Create the secret

```bash
aws secretsmanager create-secret \
  --name "dms-pg-prod" \
  --secret-string '{
    "username": "dms_user",
    "password": "<password>",
    "engine": "postgres",
    "host": "prod-db.cluster-abc123.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "dbInstanceIdentifier": "prod-db"
  }' \
  --region us-east-1
```

### Grant DMS role access

The DMS VPC role (`dms-vpc-role`) or the specified Secrets Manager
access role must have `secretsmanager:GetSecretValue`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:dms-pg-prod-*"
  }]
}
```

### Create endpoint with Secrets Manager

```bash
aws dms create-endpoint \
  --endpoint-identifier "pg-source-prod" \
  --endpoint-type source \
  --engine-name postgres \
  --secrets-manager-access-role-arn "arn:aws:iam::123456789012:role/dms-vpc-role" \
  --secrets-manager-secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:dms-pg-prod-abc123" \
  --database-name analytics \
  --ssl-mode verify-full \
  --certificate-arn "arn:aws:dms:us-east-1:123456789012:cert:prod-ca-cert" \
  --extra-connection-attributes "PluginName=pglogical" \
  --region us-east-1
```

### After secret rotation

Secrets Manager rotation changes the database password but does NOT
update the DMS endpoint. After rotation:

```bash
# Re-test the endpoint connection
aws dms test-connection \
  --replication-instance-arn "arn:aws:dms:us-east-1:123456789012:rep:rep-instance-prod" \
  --endpoint-arn "arn:aws:dms:us-east-1:123456789012:endpoint:pg-source-prod" \
  --region us-east-1
```

If the test fails after rotation, the endpoint may need to be modified
or re-created.

## Connection troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Connection test timeout | Security group / NACL blocking | Allow inbound from replication instance SG on DB port |
| Connection test auth failure | Wrong credentials or stale secret | Verify secret payload; re-test after rotation |
| SSL handshake failure | Missing/expired certificate | Import/re-import the CA certificate |
| CDC task fails immediately | Source CDC prerequisites not met | Check wal_level, supplemental logging, binary log config |
| CDC latency increasing | Source DB under load | Increase replication instance class; tune poll intervals |

## Terraform example

```hcl
resource "aws_dms_endpoint" "pg_source" {
  endpoint_id                  = "pg-source-prod"
  endpoint_type                = "source"
  engine_name                  = "postgres"
  server_name                  = "prod-db.cluster-abc123.us-east-1.rds.amazonaws.com"
  port                         = 5432
  database_name                = "analytics"
  ssl_mode                     = "verify-full"
  certificate_arn              = aws_dms_certificate.prod_ca.arn
  kms_key_arn                  = aws_kms_key.dms.arn

  secrets_manager_access_role_arn = aws_iam_role.dms_vpc.arn
  secrets_manager_secret_id       = aws_secretsmanager_secret.dms_pg_prod.arn

  extra_connection_attributes = "PluginName=pglogical;slotName=dms_replication_slot"

  tags = {
    Environment = "production"
    MigrationType = "cdc"
  }
}
```
