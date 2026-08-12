# Table Bucket Policy and Integrations — S3 Table Bucket Deployer

Deep reference on S3 table bucket policy (separate from regular S3
bucket policy, uses s3tables actions, applied via put-table-bucket-
policy), Apache Iceberg REST catalog for Athena integration, and Lake
Formation fine-grained access control for S3 Tables. Loaded on demand
by the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Table bucket policy fundamentals

### Why table bucket policy is separate from S3 bucket policy

Regular S3 buckets use `s3:PutBucketPolicy` / `aws s3api put-bucket-
policy` with `s3:*` IAM actions. S3 table buckets use a COMPLETELY
SEPARATE policy type: `s3tables:PutTableBucketPolicy` /
`aws s3tables put-table-bucket-policy` with `s3tables:*` IAM actions.

This separation exists because table buckets are a distinct resource
type — they contain namespaces and tables, not objects. The policy
actions reflect this: `s3tables:GetTable`, `s3tables:ListTables`,
`s3tables:GetNamespace`, etc.

### Table bucket policy structure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::999999999999:root"
      },
      "Action": [
        "s3tables:GetTableBucket",
        "s3tables:ListNamespaces",
        "s3tables:ListTables",
        "s3tables:GetTable",
        "s3tables:GetNamespace"
      ],
      "Resource": "arn:aws:s3tables:us-east-1:123456789012:bucket/shared-tables/*"
    }
  ]
}
```

### Available s3tables IAM actions

| Action | Description |
|---|---|
| `s3tables:CreateTableBucket` | Create a table bucket |
| `s3tables:DeleteTableBucket` | Delete a table bucket |
| `s3tables:GetTableBucket` | Describe a table bucket |
| `s3tables:ListTableBuckets` | List table buckets in account |
| `s3tables:PutTableBucketPolicy` | Apply a table bucket policy |
| `s3tables:GetTableBucketPolicy` | Retrieve a table bucket policy |
| `s3tables:CreateNamespace` | Create a namespace |
| `s3tables:DeleteNamespace` | Delete a namespace |
| `s3tables:GetNamespace` | Describe a namespace |
| `s3tables:ListNamespaces` | List namespaces in a table bucket |
| `s3tables:CreateTable` | Create a table |
| `s3tables:DeleteTable` | Delete a table |
| `s3tables:GetTable` | Describe a table |
| `s3tables:ListTables` | List tables in a namespace |
| `s3tables:UpdateTableMetadataLocation` | Update table metadata |
| `s3tables:GetTableMetadataLocation` | Get table metadata location |
| `s3tables:UpdateTableMaintenanceConfiguration` | Update maintenance |
| `s3tables:GetTableMaintenanceConfiguration` | View maintenance |

### Applying a table bucket policy

```bash
TABLE_BUCKET_ARN="arn:aws:s3tables:us-east-1:123456789012:bucket/shared-tables"

aws s3tables put-table-bucket-policy \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --resource-policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::999999999999:root"
        },
        "Action": [
          "s3tables:GetTableBucket",
          "s3tables:ListNamespaces",
          "s3tables:ListTables",
          "s3tables:GetTable",
          "s3tables:GetNamespace"
        ],
        "Resource": "arn:aws:s3tables:us-east-1:123456789012:bucket/shared-tables/*"
      }
    ]
  }' \
  --region us-east-1
```

### Verifying a table bucket policy

```bash
aws s3tables get-table-bucket-policy \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --region us-east-1
```

### Common policy mistake: using s3 instead of s3tables

```bash
# WRONG — this does NOT work on a table bucket
aws s3api put-bucket-policy \
  --bucket shared-tables \
  --policy '{"Statement":[{"Effect":"Allow","Action":"s3:GetObject",...}]}'

# CORRECT — use s3tables API with s3tables actions
aws s3tables put-table-bucket-policy \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/shared-tables \
  --resource-policy '{"Statement":[{"Effect":"Allow","Action":"s3tables:GetTable",...}]}'
```

## Cross-account access via table bucket policy

### Granting read access to another account

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::999999999999:root"
      },
      "Action": [
        "s3tables:GetTableBucket",
        "s3tables:ListNamespaces",
        "s3tables:GetNamespace",
        "s3tables:ListTables",
        "s3tables:GetTable"
      ],
      "Resource": "arn:aws:s3tables:us-east-1:123456789012:bucket/shared-tables/*"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::999999999999:root"
      },
      "Action": [
        "s3tables:GetTableBucket"
      ],
      "Resource": "arn:aws:s3tables:us-east-1:123456789012:bucket/shared-tables"
    }
  ]
}
```

**Note:** the second statement targets the bucket ARN itself (without
`/*`), not just the resources within it. Both statements are needed for
cross-account access.

### Cross-account requirements

The target account (999999999999) also needs an IAM policy granting
`s3tables:*` permissions on the resource:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3tables:GetTableBucket",
        "s3tables:ListNamespaces",
        "s3tables:GetNamespace",
        "s3tables:ListTables",
        "s3tables:GetTable"
      ],
      "Resource": "arn:aws:s3tables:us-east-1:123456789012:bucket/shared-tables/*"
    }
  ]
}
```

Both the table bucket policy (in the owner account) and the IAM policy
(in the target account) must allow the access.

## Iceberg REST catalog for Athena integration

### How Athena accesses S3 Tables

Athena does NOT access S3 Tables by specifying an S3 path. Instead, it
uses the Apache Iceberg REST catalog endpoint. The REST catalog provides
table metadata (schema, partition spec, manifest list, snapshot info)
that Athena needs to plan and execute queries.

```text
Integration flow:
  1. S3 Table Bucket → automatically provisions an Iceberg REST catalog
  2. Athena workgroup → configured to use the REST catalog
  3. Query execution:
     a. Athena sends a "load table" request to the REST catalog
     b. REST catalog returns Iceberg table metadata
     c. Athena plans the query using the metadata
     d. Athena reads data files from the table bucket
     e. Results returned to the user
```

### Configuring Athena

The Athena workgroup must be configured to use the S3 Tables catalog.
This is done through the Athena console or API:

```bash
# Verify Athena can access the S3 Tables catalog
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name sales_analytics \
  --work-group primary \
  --region us-east-1
```

If the S3 Tables catalog is not registered with Athena, you need to
register it:

```bash
# Register the S3 Tables catalog with Athena (if not auto-registered)
aws athena create-data-catalog \
  --name S3TablesCatalog \
  --type ICEBERG_REST \
  --parameters "metadata-directory=s3://athena-metadata/,rest-catalog-endpoint=<endpoint>" \
  --region us-east-1
```

### Querying S3 Tables via Athena

```sql
-- List tables in the namespace
SHOW TABLES IN sales_analytics;

-- Query the table
SELECT order_id, customer_id, amount, status
FROM sales_analytics.orders
WHERE order_date >= DATE '2026-08-01'
ORDER BY amount DESC;

-- Time travel
SELECT * FROM sales_analytics.orders
FOR SYSTEM_TIME AS OF TIMESTAMP '2026-08-01 00:00:00';

-- DDL operations (Iceberg v2)
ALTER TABLE sales_analytics.orders ADD COLUMNS (discount double);

-- DML operations (Iceberg v2)
UPDATE sales_analytics.orders SET status = 'shipped' WHERE order_id = 12345;
```

### Common Athena integration pitfalls

1. **Pointing Athena at an S3 path.** S3 Tables are NOT queried via
   `s3://bucket/path`. They are queried via the REST catalog using
   `namespace.table` notation. Using S3 paths results in "table not
   found."

2. **Missing Lake Formation grants.** If Lake Formation is enabled in
   the account, Athena queries fail without LF grants on the table.
   Always grant SELECT permissions to the Athena query role.

3. **Wrong Athena workgroup.** The Athena workgroup must be configured
   to use the S3 Tables catalog. A workgroup pointing at the default
   Glue Data Catalog will not see S3 Tables.

4. **Using the wrong format version.** If the table is Iceberg v1,
   UPDATE/DELETE/MERGE INTO operations fail with "not supported." Use
   Iceberg v2 for row-level operations.

## Lake Formation integration

### Why Lake Formation matters for S3 Tables

Lake Formation provides centralized, fine-grained access control for
S3 Tables. When LF is enabled, IAM policies alone are NOT sufficient —
Lake Formation grants are also required. Without LF grants, Athena
queries fail with "Insufficient Lake Formation permissions."

### Granting table-level access

```bash
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --permissions SELECT DESCRIBE \
  --resource '{"Table": {"DatabaseName": "sales_analytics", "Name": "orders"}}' \
  --region us-east-1
```

### Granting column-level access

```bash
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --permissions SELECT \
  --resource '{
    "TableWithColumns": {
      "DatabaseName": "sales_analytics",
      "Name": "orders",
      "ColumnNames": ["order_id", "customer_id", "order_date", "status"]
    }
  }' \
  --region us-east-1
```

### Granting with column wildcard

```bash
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --permissions SELECT \
  --resource '{
    "TableWithColumns": {
      "DatabaseName": "sales_analytics",
      "Name": "orders",
      "ColumnWildcard": {}
    }
  }' \
  --region us-east-1
```

### Granting namespace-level access

```bash
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --permissions DESCRIBE \
  --resource '{"Database": {"Name": "sales_analytics"}}' \
  --region us-east-1
```

### Lake Formation permission model

| Permission | Scope | What it allows |
|---|---|---|
| `SELECT` | Table or column | Read data from the table or columns |
| `DESCRIBE` | Table or namespace | View table metadata (schema, etc.) |
| `ALTER` | Table | Modify table schema or properties |
| `DROP` | Table or namespace | Delete the table or namespace |
| `INSERT` | Table | Write data to the table |
| `DELETE` | Table | Delete rows (Iceberg v2 only) |

### Verifying Lake Formation permissions

```bash
# List permissions for a principal
aws lakeformation list-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --region us-east-1
```

### Common Lake Formation pitfalls

1. **LF enabled but no grants.** If Lake Formation is enabled in the
   account, ALL table access must go through LF grants. IAM policies
   alone are not sufficient. This is the most common cause of "access
   denied" errors in Athena.

2. **Granting on the wrong database name.** The database name in LF
   must match the namespace name in S3 Tables. If the namespace is
   `sales_analytics`, the LF database name is `sales_analytics`.

3. **Forgetting to grant DESCRIBE.** Without DESCRIBE on the database
   (namespace), Athena cannot list tables. Grant both DESCRIBE on the
   namespace and SELECT on the table.

4. **Column-level grants too restrictive.** If you grant column-level
   SELECT on specific columns, any query selecting other columns fails.
   Use `ColumnWildcard` for full table access unless you specifically
   need column-level restrictions (e.g., PII masking).

## Terraform policy and integration example

```hcl
# Table bucket policy
resource "aws_s3tables_table_bucket_policy" "cross_account" {
  table_bucket_arn = aws_s3tables_table_bucket.shared.arn
  resource_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::999999999999:root" }
        Action = [
          "s3tables:GetTableBucket",
          "s3tables:ListNamespaces",
          "s3tables:GetNamespace",
          "s3tables:ListTables",
          "s3tables:GetTable"
        ]
        Resource = "${aws_s3tables_table_bucket.shared.arn}/*"
      }
    ]
  })
}

# Lake Formation grant
resource "aws_lakeformation_permissions" "athena_access" {
  principal   = "arn:aws:iam::123456789012:role/AthenaUserRole"
  permissions = ["SELECT", "DESCRIBE"]

  table {
    catalog_id    = "123456789012"
    database_name = "sales_analytics"
    name          = "orders"
  }
}
```
