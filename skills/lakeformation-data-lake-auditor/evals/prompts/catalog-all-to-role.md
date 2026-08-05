# Eval prompt: catalog-all-to-role

Audit the following Lake Formation data-lake configuration for security
exposure. Emit the standard VERDICT block (LAKE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit target (catalog): 111111111111 (catalog-all-to-role)
Lake Formation enabled: true (describe-organization)
Data lake settings (get-data-lake-settings):
  DataLakeAdmins:
    - arn:aws:iam::111111111111:role/lf-break-glass
Registered locations (list-resources):
  - ResourceArn: arn:aws:s3:::prod-datalake/catalog/
    RoleArn: arn:aws:iam::111111111111:role/aws-service-role/lakeformation/ApplicationRole
Data cells filters (list-data-cells-filter): []
Permissions (list-permissions):

```json
{
  "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/data-engineer"},
  "Resource": {"Catalog": {}},
  "Permissions": ["ALL"],
  "PermissionsWithGrantOptions": ["ALL"]
}
```
