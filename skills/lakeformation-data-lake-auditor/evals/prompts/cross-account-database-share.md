# Eval prompt: cross-account-database-share

Audit the following Lake Formation data-lake configuration for security
exposure. Emit the standard VERDICT block (LAKE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit target (catalog): 111111111111 (cross-account-database-share)
Lake Formation enabled: true (describe-organization)
Data lake settings (get-data-lake-settings):
  DataLakeAdmins:
    - arn:aws:iam::111111111111:role/lf-break-glass
Registered locations (list-resources):
  - ResourceArn: arn:aws:s3:::prod-datalake/finance/
    RoleArn: arn:aws:iam::111111111111:role/aws-service-role/lakeformation/ApplicationRole
Data cells filters (list-data-cells-filter): []
Permissions (list-permissions):

```json
[
  {
    "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::222222222222:root"},
    "Resource": {"Database": {"Name": "finance", "CatalogId": "111111111111"}},
    "Permissions": ["DESCRIBE"],
    "PermissionsWithGrantOptions": []
  },
  {
    "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::222222222222:role/partner-analyst"},
    "Resource": {"TableWithColumns": {"DatabaseName": "finance", "Name": "transactions", "CatalogId": "111111111111", "ColumnNames": ["txn_id", "amount", "currency"]}},
    "Permissions": ["DESCRIBE", "SELECT"],
    "PermissionsWithGrantOptions": []
  }
]
```
