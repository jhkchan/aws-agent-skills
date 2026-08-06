# Eval prompt: clean-column-scoped-with-filter

Audit the following Lake Formation data-lake configuration for security
exposure. Emit the standard VERDICT block (LAKE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit target (catalog): 111111111111 (clean-column-scoped-with-filter)
Lake Formation enabled: true (describe-organization)
Data lake settings (get-data-lake-settings):
  DataLakeAdmins:
    - arn:aws:iam::111111111111:role/lf-break-glass
Registered locations (list-resources):
  - ResourceArn: arn:aws:s3:::prod-datalake/sales/
    RoleArn: arn:aws:iam::111111111111:role/aws-service-role/lakeformation/ApplicationRole
Data cells filters (list-data-cells-filter):
  - TableName: orders
    DatabaseName: sales
    Name: region-us-filter
    RowFilter: {"FilterExpression": "region = 'US'"}
LF-tags on table orders:
  - data_classification=internal
Table storage descriptor:
  - orders location: s3://prod-datalake/sales/orders/  (under registered location)
Data cells filter grant wiring:
  - The SELECT grant below is scoped by the region-us-filter DataCellsFilter.
Permissions (list-permissions):

```json
{
  "Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/sales-analyst"},
  "Resource": {"TableWithColumns": {"DatabaseName": "sales", "Name": "orders", "CatalogId": "111111111111", "ColumnNames": ["order_id", "total", "region"]}},
  "Permissions": ["SELECT"],
  "PermissionsWithGrantOptions": []
}
```
