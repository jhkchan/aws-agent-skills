# Eval prompt: grant-on-unregistered-path

Audit the following Lake Formation data-lake configuration for security
exposure. Emit the standard VERDICT block (LAKE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit target (catalog): 111111111111 (grant-on-unregistered-path)
Lake Formation enabled: true (describe-organization)
Data lake settings (get-data-lake-settings):
  DataLakeAdmins:
    - arn:aws:iam::111111111111:role/lf-break-glass
Registered locations (list-resources):
  - ResourceArn: arn:aws:s3:::prod-datalake/operations/
    RoleArn: arn:aws:iam::111111111111:role/aws-service-role/lakeformation/ApplicationRole
Data cells filters (list-data-cells-filter): []
Table storage descriptor:
  - campaigns location: s3://separate-unregistered-bucket/marketing/campaigns/  (NOT under any registered location)
Permissions (list-permissions):

```json
{
  "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/analyst"},
  "Resource": {"TableWithColumns": {"DatabaseName": "marketing", "Name": "campaigns", "CatalogId": "111111111111", "ColumnNames": ["clicks", "impressions", "spend"]}},
  "Permissions": ["SELECT"],
  "PermissionsWithGrantOptions": []
}
```
