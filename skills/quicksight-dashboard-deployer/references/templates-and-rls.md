# Templates and Row-Level Security — QuickSight Dashboard Deployer

Deep reference on template-based multi-tenant dashboard deployment,
template version management, row-level security (RLS) mechanisms, and
the RLS rules dataset pattern. Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays scannable.

## Template fundamentals

A QuickSight template captures the definition of an analysis or
dashboard (visuals, layouts, calculated fields, parameters) as an
immutable, versioned artifact. Templates are the deployment vehicle for
multi-tenant and cross-account dashboard replication.

### Template versioning

Each template update creates a new version. Versions are immutable.

```bash
# List template versions
aws quicksight list-template-versions \
  --aws-account-id 123456789012 \
  --template-id sales-template \
  --region us-east-1

# Describe a specific version
aws quicksight describe-template \
  --aws-account-id 123456789012 \
  --template-id sales-template \
  --version-number 2 \
  --region us-east-1
```

### Cross-account template sharing

To deploy a template across accounts:

1. In the source account, create the template.
2. Grant the target account permission to read the template.
3. In the target account, create a dashboard FROM the source template.

```bash
# Source account: grant cross-account permission
aws quicksight update-template-permissions \
  --aws-account-id 123456789012 \
  --template-id sales-template \
  --grant-permissions '{"Principal":"arn:aws:quicksight:us-east-1:999999999999:user/default/deploy-user","Actions":["quicksight:DescribeTemplate"]}' \
  --region us-east-1

# Target account: create dashboard from source template
aws quicksight create-dashboard \
  --aws-account-id 999999999999 \
  --dashboard-id tenant-b-sales \
  --source-entity '{"SourceTemplate":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:template/sales-template","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:999999999999:dataset/ds-tenant-b-sales"}]}}' \
  --region us-east-1
```

### Schema match requirement

The target dataset's schema MUST match the source dataset's schema
(column names and types). If the template was built from a dataset with
columns `[order_id, region, revenue]`, the target dataset must have the
same columns. Schema mismatches cause silent failures or missing
visuals.

## Row-level security (RLS)

### How RLS works

RLS filters rows at the dataset level before data reaches any visual.
When a reader opens a dashboard, QuickSight checks the reader's identity
(user ARN or group ARN) against RLS rules. Only matching rows are
returned.

### RLS via rules dataset

The RLS rules dataset maps users/groups to allowed column values.

```text
RLS rules dataset format:
  UserName           | Region
  -------------------|--------
  reader@east.com    | East
  reader@west.com    | West
  group:managers     | (all values — wildcard or explicit)
```

**Column mapping:** the RLS rules dataset has one column per filtered
dimension. The column name in the RLS dataset must match a column in the
source dataset. In the example above, `Region` in the RLS rules dataset
corresponds to `Region` in the source dataset.

### Enabling RLS

```bash
aws quicksight update-data-set \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --row-level-permission-data-set '{
    "Arn": "arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-rls",
    "PermissionPolicy": "GRANT_ACCESS",
    "FormatVersion": "VERSION_1",
    "Namespace": "default",
    "Status": "ENABLED"
  }' \
  --region us-east-1
```

- **GRANT_ACCESS:** users in the rules dataset can see matching rows.
  Everyone else sees nothing.
- **DENY_ACCESS:** users in the rules dataset are blocked from matching
  rows. Everyone else sees everything.

### RLS for embedded dashboards

For embedded dashboards (via `generate-embedding-url`), the session
identity is passed as a parameter. RLS rules apply based on the session
identity, not the QuickSight user account.

```bash
aws quicksight generate-embedding-url-for-registered-user \
  --aws-account-id 123456789012 \
  --experience-configuration '{"Dashboard":{"InitialDashboardId":"sales-dashboard"}}' \
  --user-arn "arn:aws:quicksight:us-east-1:123456789012:user/default/reader@east.com" \
  --session-lifetime-in-minutes 120 \
  --region us-east-1
```

### Multi-tenant RLS pattern

For strict tenant isolation:

1. Create a separate dataset per tenant (each pointing at tenant data).
2. Create a separate RLS rules dataset per tenant.
3. Deploy the same template-based dashboard for each tenant.
4. Apply the tenant-specific RLS rules.

For shared-dataset multi-tenancy:

1. One dataset with a `tenant_id` column.
2. RLS rules map each user to their `tenant_id`.
3. All users share one dashboard, each seeing only their rows.

### RLS troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Reader sees no data | RLS rules don't match the reader's identity | Add the reader to the RLS rules dataset |
| Reader sees all data | RLS is defined but not ENABLED | Set `Status: ENABLED` in update-data-set |
| RLS column not filtering | Column name mismatch between RLS and source | Ensure exact column name match |
| Group-based RLS not working | Group ARN format incorrect | Use `group:<group-name>` in the UserName column |

## Terraform RLS example

```hcl
# RLS rules dataset
resource "aws_quicksight_data_set" "sales_rls" {
  data_set_id = "ds-sales-rls"
  name        = "Sales RLS Rules"
  import_mode = "SPICE"

  physical_table_map {
    physical_table_map_id = "rls-table"
    relational_table {
      data_source_arn = aws_quicksight_data_source.athena.arn
      schema          = "rls"
      name            = "sales_rls_rules"
      input_columns {
        name = "UserName"
        type = "STRING"
      }
      input_columns {
        name = "Region"
        type = "STRING"
      }
    }
  }
}

# Enable RLS on the main dataset
resource "aws_quicksight_data_set" "sales" {
  data_set_id = "ds-sales-metrics"
  name        = "Sales Metrics"
  import_mode = "SPICE"

  row_level_permission_data_set {
    arn              = aws_quicksight_data_set.sales_rls.arn
    permission_policy = "GRANT_ACCESS"
    format_version    = "VERSION_1"
    namespace         = "default"
    status            = "ENABLED"
  }

  physical_table_map {
    # ...
  }
}
```


## Step 6 — Template-based deployment commands

**Create template from analysis:**

```bash
aws quicksight create-template \
  --aws-account-id 123456789012 \
  --template-id "sales-template" \
  --name "Sales Dashboard Template" \
  --source-entity '{"SourceAnalysis":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:analysis/sales-analysis","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-metrics"}]}}' \
  --version-description "v1.0" \
  --region us-east-1
```

**Create dashboard from template (per tenant):**

```bash
aws quicksight create-dashboard \
  --aws-account-id 123456789012 \
  --dashboard-id "tenant-a-sales" \
  --name "Tenant A Sales Dashboard" \
  --source-entity '{"SourceTemplate":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:template/sales-template","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-tenant-a-sales"}]}}' \
  --version-description "Tenant A v1" \
  --region us-east-1
```

**Propagate template update to tenant dashboards:**

```bash
aws quicksight update-template \
  --aws-account-id 123456789012 \
  --template-id "sales-template" \
  --source-entity '{"SourceAnalysis":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:analysis/sales-analysis","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-metrics"}]}}' \
  --region us-east-1

aws quicksight update-dashboard \
  --aws-account-id 123456789012 \
  --dashboard-id "tenant-a-sales" \
  --source-entity '{"SourceTemplate":{"Arn":"arn:aws:quicksight:us-east-1:123456789012:template/sales-template","DataSetReferences":[{"DataSetPlaceholder":"sales-data","DataSetArn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-tenant-a-sales"}]}}' \
  --version-description "Updated from template v2" \
  --region us-east-1
```


## Step 7 — Row-level security commands

**Create RLS rules dataset (maps users to allowed column values):**

```bash
aws quicksight create-data-set \
  --aws-account-id 123456789012 \
  --data-set-id "ds-sales-rls" \
  --name "Sales RLS Rules" \
  --import-mode SPICE \
  --physical-table-map '{"rls-table":{"RelationalTable":{"DataSourceArn":"arn:aws:quicksight:us-east-1:123456789012:datasource/ds-athena-prod","Schema":"rls","Name":"sales_rls_rules","InputColumns":[{"Name":"UserName","Type":"STRING"},{"Name":"Region","Type":"STRING"}]}}}' \
  --region us-east-1
```

**Enable RLS on the dataset using the RLS rules dataset:**

```bash
aws quicksight update-data-set \
  --aws-account-id 123456789012 \
  --data-set-id "ds-sales-metrics" \
  --row-level-permission-data-set '{"Arn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-rls","PermissionPolicy":"GRANT_ACCESS","FormatVersion":"VERSION_1","Namespace":"default","Status":"ENABLED"}' \
  --region us-east-1
```
