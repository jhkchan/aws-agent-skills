# Baseline (no-skill) — column-level-security

> This is the response a model produces **without** the skill definition.
> It grants table-level SELECT on the entire transactions table
> (including PII columns), skips the data cells filter entirely, and does
> not create a row filter for regional access. The principal can see all
> rows and all columns including PII — a security violation.

---

Here are the commands to deploy your column-level security:

```bash
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/RegionalAnalystRole"}' \
  --permissions SELECT DESCRIBE \
  --resource '{"Table": {"DatabaseName": "analytics_db", "Name": "transactions", "CatalogId": "123456789012"}}'
```

Your permissions should be applied.
