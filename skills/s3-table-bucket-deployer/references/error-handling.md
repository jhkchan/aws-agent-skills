# Error Handling — s3-table-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Error handling

### create-table fails with namespace not found
- The namespace does not exist. Create it first with
  `create-namespace`, then retry.

### put-table-bucket-policy fails
- Policy uses `s3:*` actions instead of `s3tables:*`. Rewrite with
  `s3tables:GetTable`, `s3tables:ListTables`, etc.

### Athena returns "table not found"
- Athena is not configured with the Iceberg REST catalog. Verify the
  workgroup references the REST catalog endpoint. Also verify Lake
  Formation grants exist.

### Athena returns "Insufficient Lake Formation permissions"
- Use `grant-permissions` to grant SELECT on the table to the query
  role.

### Table maintenance not running
- Check `get-table-maintenance-configuration`. May be DISABLED, or
  the table may not have enough data to trigger compaction (below
  minInputFiles threshold).

### Iceberg v1 table cannot do UPDATE/DELETE
- v1 does not support row-level operations. Create a new table with
  format-version 2 and migrate data.
