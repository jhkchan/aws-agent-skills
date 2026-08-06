# Eval prompt: empty-admins-and-iam-mixed-mode

Audit the following Lake Formation data-lake configuration for security
exposure. Emit the standard VERDICT block (LAKE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit target (catalog): 111111111111 (empty-admins-and-iam-mixed-mode)
Lake Formation enabled: true (describe-organization)
Data lake settings (get-data-lake-settings):
  DataLakeAdmins: []
Registered locations (list-resources):
  - ResourceArn: arn:aws:s3:::prod-datalake/legacy/
    RoleArn: arn:aws:iam::111111111111:role/aws-service-role/lakeformation/ApplicationRole
Data cells filters (list-data-cells-filter): []
Table storage descriptor:
  - legacy_table location: s3://prod-datalake/legacy/legacy_table/  (under registered location)
Permissions (list-permissions):

```json
[
  {
    "Principal": {"DataLakePrincipalIdentifier": "IAMAllowedPrincipals"},
    "Resource": {"Database": {"Name": "legacy_db", "CatalogId": "111111111111"}},
    "Permissions": ["ALL"],
    "PermissionsWithGrantOptions": []
  },
  {
    "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/legacy-analyst"},
    "Resource": {"TableWithColumns": {"DatabaseName": "legacy_db", "Name": "legacy_table", "CatalogId": "111111111111", "ColumnNames": ["col1", "col2"]}},
    "Permissions": ["DESCRIBE", "SELECT"],
    "PermissionsWithGrantOptions": []
  }
]
```
