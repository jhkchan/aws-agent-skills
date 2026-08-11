# CLI Commands and IaC — Lake Formation Permissions Deployer

Full copy-pasteable CLI command sequence for all 10 deployment steps.
Variables to substitute: `<account-id>`, `<region>`, `<admin-role>`,
`<principal-arn>`, `<database>`, `<table>`, `<tag-key>`, `<tag-values>`,
`<column-names>`, `<link-name>`, `<filter-name>`, `<filter-expression>`,
`<sso-instance-arn>`, `<datazone-domain-id>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm data lake admin is registered
aws lakeformation list-data-lake-settings \
  --query 'DataLakeSettings.DataLakeAdmins'

# Confirm Glue database exists
aws glue get-database --name <database> 2>/dev/null || echo "Database does not exist"

# Confirm Glue table exists
aws glue get-table --database-name <database> --name <table> 2>/dev/null || echo "Table does not exist"

# Confirm IAM principal exists
aws iam get-role --role-name <role-name> 2>/dev/null || echo "Role does not exist"

# Confirm S3 data location is registered
aws lakeformation list-resources \
  --query 'ResourceInfoList[*].ResourceArn'

# Confirm LF-tags exist
aws lakeformation list-lf-tags

# Confirm Identity Center instance (if SSO integration)
aws sso-admin list-instances --query 'Instances[*].InstanceArn'

# Confirm DataZone domain (if DataZone integration)
aws datazone list-domains --query 'items[*].id'
```

## Step 1: Register data lake admin

```bash
aws lakeformation put-data-lake-settings \
  --data-lake-settings '{
    "DataLakeAdmins": [
      {"DataLakePrincipalIdentifier": "arn:aws:iam::<account-id>:role/<admin-role>"}
    ],
    "CreateDatabaseDefaultPermissions": [
      {"Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::<account-id>:role/<admin-role>"}, "Permissions": ["ALL"]}
    ],
    "CreateTableDefaultPermissions": [
      {"Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::<account-id>:role/<admin-role>"}, "Permissions": ["ALL"]}
    ]
  }'
```

## Step 2: Create LF-tag keys and values

```bash
aws lakeformation create-lf-tag \
  --tag-key environment \
  --tag-values production staging dev

aws lakeformation create-lf-tag \
  --tag-key department \
  --tag-values finance engineering marketing

aws lakeformation create-lf-tag \
  --tag-key sensitivity \
  --tag-values public internal restricted pii
```

Update LF-tag values (add only):

```bash
aws lakeformation update-lf-tag \
  --tag-key department \
  --to-add-values operations legal
```

## Step 3: Attach LF-tags to resources

```bash
# Database-level LF-tags
aws lakeformation add-lf-tags-to-resource \
  --resource '{"Database": {"Name": "<database>"}}' \
  --lf-tags '[{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]'

# Table-level LF-tags
aws lakeformation add-lf-tags-to-resource \
  --resource '{"Table": {"DatabaseName": "<database>", "Name": "<table>"}}' \
  --lf-tags '[{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "sensitivity", "TagValues": ["restricted"]}]'

# Column-level LF-tags (for PII columns)
aws lakeformation add-lf-tags-to-resource \
  --resource '{"TableWithColumns": {"DatabaseName": "<database>", "Name": "<table>", "ColumnNames": ["ssn", "credit_card"]}}' \
  --lf-tags '[{"TagKey": "sensitivity", "TagValues": ["pii"]}]'
```

## Step 4: Grant LF-tag-based permissions

```bash
# LF-tag-based grant on TABLE resource type
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions SELECT DESCRIBE \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]}}'

# LF-tag-based grant on DATABASE resource type
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions DESCRIBE ALTER \
  --resource '{"LFTagPolicy": {"ResourceType": "DATABASE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}]}}'

# Named resource grant (specific table)
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions SELECT DESCRIBE \
  --resource '{"Table": {"DatabaseName": "<database>", "Name": "<table>", "CatalogId": "<account-id>"}}'
```

## Step 5: Column-level security

```bash
# Column grant (grant subset of columns — PII columns excluded)
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions SELECT \
  --resource '{"TableWithColumns": {"DatabaseName": "<database>", "Name": "<table>", "ColumnNames": ["transaction_id", "amount", "currency", "timestamp", "merchant"]}}'

# Explicit revoke/deny on PII columns
aws lakeformation batch-revoke-permissions \
  --entries '[{
    "Id": "deny-pii",
    "Principal": {"DataLakePrincipalIdentifier": "<principal-arn>"},
    "Permissions": ["SELECT"],
    "Resource": {"TableWithColumns": {"DatabaseName": "<database>", "Name": "<table>", "ColumnNames": ["ssn", "credit_card"]}}
  }]'
```

## Step 6: Resource links (cross-database)

```bash
# Create resource link
aws lakeformation create-resource-link \
  --resource-link-input '{
    "Name": "<link-name>",
    "DatabaseName": "<target-database>",
    "TableIdentifier": "<source-table>"
  }'

# Grant DESCRIBE on the resource link
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions DESCRIBE \
  --resource '{"Table": {"DatabaseName": "<target-database>", "Name": "<link-name>", "CatalogId": "<account-id>"}}'

# Grant SELECT on the underlying target table
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions SELECT \
  --resource '{"Table": {"DatabaseName": "<source-database>", "Name": "<source-table>", "CatalogId": "<account-id>"}}'
```

## Step 7: Data cells filter

```bash
# Create data cells filter
aws lakeformation create-data-cells-filter \
  --table-data '{
    "TableCatalogId": "<account-id>",
    "DatabaseName": "<database>",
    "TableName": "<table>",
    "Name": "<filter-name>",
    "RowFilter": {
      "FilterExpression": "<filter-expression>",
      "AllRowsWildcard": {}
    },
    "ColumnNames": ["transaction_id", "amount", "currency", "timestamp", "merchant", "region"],
    "ColumnWildcard": {"ExcludedColumnNames": ["ssn", "credit_card"]},
    "VersionId": "1"
  }'

# Grant access to the data cells filter
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "<principal-arn>"}' \
  --permissions SELECT \
  --resource '{"DataCellsFilter": {"DatabaseName": "<database>", "TableName": "<table>", "Name": "<filter-name>", "CatalogId": "<account-id>"}}'
```

## Step 8: IAM Identity Center integration

```bash
# Create Lake Formation application in Identity Center
aws sso-admin create-application \
  --instance-arn <sso-instance-arn> \
  --application-provider-configuration '{"ApplicationProviderArn": "arn:aws:sso:::applicationProvider/lakeformation"}' \
  --name "LakeFormation-SSO"

# Grant permissions to Identity Center group/permission set
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:sso:::permissionSet/<instance-id>/<ps-id>"}' \
  --permissions SELECT DESCRIBE \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}]}}'
```

## Step 9: LF-tags with Amazon DataZone

```bash
# Create DataZone domain
aws datazone create-domain \
  --name "analytics-domain" \
  --domain-execution-role arn:aws:iam::<account-id>:role/DataZoneExecutionRole

# Subscribe a project to an LF-tag-backed listing
aws datazone create-subscription \
  --domain-identifier <datazone-domain-id> \
  --request-name "analytics-team-subscription" \
  --subscribed-listings '[{"ListingId": "<listing-id>"}]' \
  --subscription-request-creator "<principal-arn>"
```

## Step 10: Verification

```bash
aws lakeformation list-permissions --principal <principal-arn>
aws lakeformation list-lf-tags
aws lakeformation get-resource-lf-tags --resource '{"Database": {"Name": "<database>"}}'
aws lakeformation get-resource-lf-tags --resource '{"Table": {"DatabaseName": "<database>", "Name": "<table>"}}'
aws lakeformation list-resources
aws lakeformation describe-resource --resource-arn arn:aws:glue:<region>:<account-id>:table/<database>/<table>
aws glue get-database --name <database>
aws iam get-role --role-name <admin-role>
```

## Terraform equivalent

```hcl
# Data lake admin
resource "aws_lakeformation_data_lake_settings" "this" {
  admins = [aws_iam_role.lf_admin.arn]
}

# LF-tag keys
resource "aws_lakeformation_lf_tag" "environment" {
  tag_key   = "environment"
  tag_values = ["production", "staging", "dev"]
}

resource "aws_lakeformation_lf_tag" "department" {
  tag_key   = "department"
  tag_values = ["finance", "engineering", "marketing"]
}

# Attach LF-tags to database
resource "aws_lakeformation_resource_lf_tags" "db_tags" {
  database_name = "analytics_db"

  lf_tag {
    key   = aws_lakeformation_lf_tag.environment.tag_key
    value = "production"
  }

  lf_tag {
    key   = aws_lakeformation_lf_tag.department.tag_key
    value = "finance"
  }
}

# LF-tag-based grant
resource "aws_lakeformation_permissions" "analytics_team" {
  principal = aws_iam_role.analytics_team.arn
  permissions = ["SELECT", "DESCRIBE"]

  lf_tag_policy {
    resource_type = "TABLE"

    expression {
      key      = aws_lakeformation_lf_tag.environment.tag_key
      values   = ["production"]
    }

    expression {
      key      = aws_lakeformation_lf_tag.department.tag_key
      values   = ["finance"]
    }
  }
}

# Column-level grant
resource "aws_lakeformation_permissions" "column_grant" {
  principal = aws_iam_role.analytics_team.arn
  permissions = ["SELECT"]

  table_with_columns {
    database_name = "analytics_db"
    name          = "transactions"
    column_names  = ["transaction_id", "amount", "currency", "timestamp", "merchant"]
  }
}
```

## CloudFormation equivalent

```yaml
Resources:
  LFDataLakeSettings:
    Type: AWS::LakeFormation::DataLakeSettings
    Properties:
      Admins:
        - DataLakePrincipalIdentifier: !GetAtt LFDataLakeAdminRole.Arn

  LFEnvironmentTag:
    Type: AWS::LakeFormation::ResourceTag
    Properties:
      TagKey: environment
      TagValues:
        - production
        - staging
        - dev

  LFDatabaseTagAssociation:
    Type: AWS::LakeFormation::TagAssociation
    Properties:
      Resource:
        Database:
          Name: analytics_db
      LFTags:
        - TagKey: environment
          TagValues:
            - production
        - TagKey: department
          TagValues:
            - finance

  AnalyticsTeamPermissions:
    Type: AWS::LakeFormation::PrincipalPermissions
    Properties:
      Principal:
        DataLakePrincipalIdentifier: !GetAtt AnalyticsTeamRole.Arn
      Permissions:
        - SELECT
        - DESCRIBE
      Resource:
        LFTagPolicy:
          ResourceType: TABLE
          Expression:
            - TagKey: environment
              TagValues:
                - production
            - TagKey: department
              TagValues:
                - finance
```
