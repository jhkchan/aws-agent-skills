# Eval prompt: column-wildcard-select-no-filter

Audit the following Lake Formation data-lake configuration for security
exposure. Emit the standard VERDICT block (LAKE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit target (catalog): 111111111111 (column-wildcard-select-no-filter)
Lake Formation enabled: true (describe-organization)
Data lake settings (get-data-lake-settings):
  DataLakeAdmins:
    - arn:aws:iam::111111111111:role/lf-break-glass
Registered locations (list-resources):
  - ResourceArn: arn:aws:s3:::prod-datalake/customer/
    RoleArn: arn:aws:iam::111111111111:role/aws-service-role/lakeformation/ApplicationRole
Data cells filters (list-data-cells-filter): []
LF-tags on table customers_pii:
  - data_classification=PII
Table storage descriptor:
  - customers_pii location: s3://prod-datalake/customer/customers_pii/  (under registered location)
Permissions (list-permissions):

```json
{
  "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/analyst"},
  "Resource": {"TableWithColumns": {"DatabaseName": "customers", "Name": "customers_pii", "CatalogId": "111111111111", "ColumnWildcard": {}}},
  "Permissions": ["SELECT"],
  "PermissionsWithGrantOptions": []
}
```
