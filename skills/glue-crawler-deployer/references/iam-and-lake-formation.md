# IAM and Lake Formation — Glue Crawler Deployer

Deep reference on IAM role creation for Glue Crawlers (trust policy,
least-privilege permissions, scoped S3 and Glue resources), Lake
Formation integration (LF-enabled databases, permission grants,
LF-tags), DynamoDB export crawling, and JDBC connection configuration.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## IAM role for Glue Crawlers

### Trust policy

The crawler role must trust the Glue service principal:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "glue.amazonaws.com" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "aws:SourceAccount": "123456789012"
      }
    }
  }]
}
```

The `aws:SourceAccount` condition prevents confused-deputy attacks.

### Permissions policy — S3 crawler (least-privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::my-data-lake",
        "arn:aws:s3:::my-data-lake/events/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase", "glue:CreateDatabase",
        "glue:GetTable", "glue:CreateTable",
        "glue:UpdateTable", "glue:DeleteTableVersion",
        "glue:GetTables", "glue:GetTableVersions",
        "glue:GetPartition", "glue:GetPartitions",
        "glue:CreatePartition", "glue:BatchCreatePartition",
        "glue:UpdatePartition", "glue:DeletePartition"
      ],
      "Resource": [
        "arn:aws:glue:us-east-1:123456789012:catalog",
        "arn:aws:glue:us-east-1:123456789012:database/my_database",
        "arn:aws:glue:us-east-1:123456789012:table/my_database/*"
      ]
    }
  ]
}
```

### Permissions policy — JDBC crawler (additional)

JDBC crawlers need a Glue Connection and the ability to read the
connection credentials from Secrets Manager:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["glue:GetConnection", "glue:GetConnections"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:pg-connection-*"
    }
  ]
}
```

### Permissions policy — DynamoDB export crawler

DynamoDB export crawlers read from S3 (the export path). The
permissions are the same as the S3 crawler policy, scoped to the
export bucket:

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::my-ddb-exports",
    "arn:aws:s3:::my-ddb-exports/dynamodb/*"
  ]
}
```

### CloudWatch Logs permissions

The crawler writes logs to CloudWatch Logs. Add:

```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup", "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws-glue/crawlers:*"
}
```

## Lake Formation integration

### LF-enabled databases

When a Glue database is registered with Lake Formation, table and
partition access is governed by LF permissions, not just IAM. The
crawler role needs BOTH IAM Glue permissions AND LF permissions.

### Granting LF permissions to the crawler role

```bash
# Database-level: allow crawler to create tables
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/GlueCrawlerRole \
  --permissions CREATE_TABLE, ALTER, DROP \
  --resource '{ "Database": { "Name": "lf_analytics_db" } }'

# Table-level: allow crawler to create/modify tables
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/GlueCrawlerRole \
  --permissions ALL \
  --resource '{ "Table": { "DatabaseName": "lf_analytics_db", "Name": "*" } }'

# Optional: grant on LF-tagged resources
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/GlueCrawlerRole \
  --permissions ALL \
  --resource '{ "LFTagPolicy": { "ResourceType": "TABLE",
    "Expression": [{ "TagKey": "environment", "TagValues": ["production"] }] } }'
```

### Without LF permissions

If the database is LF-enabled and the crawler role lacks LF
permissions, the crawler fails:

```text
Error: AccessDeniedException
Message: Insufficient Lake Formation permission(s) on my_table
Required permissions: CREATE_TABLE on database lf_analytics_db
```

### LF-tag assignment by crawler

Crawlers can automatically assign LF-tags to newly created tables. This
is configured via the crawler's `LakeFormationConfiguration`:

```json
{
  "LakeFormationConfiguration": {
    "AccountId": "123456789012",
    "LFTags": [
      { "TagKey": "environment", "TagValues": ["production"] },
      { "TagKey": "source", "TagValues": ["s3-events"] }
    ]
  }
}
```

## DynamoDB export crawling

### DynamoDB export flow

```text
1. DynamoDB table → export to S3 (using export-table-to-point-in-time)
   Output format: DYNAMODB_JSON (or ION)
   S3 path: s3://my-ddb-exports/dynamodb/MyTable/AWSDynamoDB/01625000000-xxx/data/

2. Glue Crawler → crawl the S3 export path
   The crawler recognizes DYNAMODB_JSON format and infers the schema

3. Athena → query the catalog table as a normal S3 table
```

### Export to S3

```bash
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:us-east-1:123456789012:table/MyTable \
  --s3-bucket-owner 123456789012 \
  --s3-bucket my-ddb-exports \
  --s3-prefix dynamodb/MyTable/ \
  --export-format DYNAMODB_JSON \
  --export-time 1722816000
```

### Crawler configuration for DynamoDB export

Point the crawler at the export S3 path. The DYNAMODB_JSON format is
auto-detected by the crawler.

```json
{
  "Targets": {
    "S3Targets": [
      { "Path": "s3://my-ddb-exports/dynamodb/MyTable/" }
    ]
  }
}
```

## JDBC connection configuration

### Creating a Glue Connection

```bash
aws glue create-connection \
  --connection-input '{
    "Name": "pg-connection",
    "ConnectionType": "JDBC",
    "ConnectionProperties": {
      "JDBC_CONNECTION_URL": "jdbc:postgresql://db.example.com:5432/mydb",
      "USERNAME": "glue-reader",
      "PASSWORD": "secret-password"
    },
    "PhysicalConnectionRequirements": {
      "SubnetId": "subnet-abc123",
      "SecurityGroupIdList": ["sg-db-access"],
      "AvailabilityZone": "us-east-1a"
    }
  }'
```

### Connection best practices

- Store the password in Secrets Manager, not in plaintext
- The subnet and security group must allow access to the database
- The security group must have an inbound rule from the Glue VPC
- Test the connection before creating the crawler:
  `aws glue test-connection --connection-name pg-connection`

### JDBC crawler targets

```json
{
  "JdbcTargets": [
    {
      "ConnectionName": "pg-connection",
      "Path": "public/%",
      "Exclusions": ["public/temp_*"]
    }
  ]
}
```

`Path: "public/%"` crawls all tables in the `public` schema. Use
exclusions to skip temporary or staging tables.
