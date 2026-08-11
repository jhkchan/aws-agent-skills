# Baseline (no-skill) — resource-link-cross-database

> This is the response a model produces **without** the skill definition.
> It creates the resource link but only grants DESCRIBE on the link,
> forgetting to grant SELECT on the underlying target table. When the
> reporting team queries the link, they get "access denied" on the
> underlying table even though they can see the link in the catalog.

---

Here are the commands to deploy your cross-database resource link:

```bash
aws lakeformation create-resource-link \
  --resource-link-input '{
    "Name": "finance_transactions_link",
    "DatabaseName": "reporting_db",
    "TableIdentifier": "transactions"
  }'

aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/ReportingTeamRole"}' \
  --permissions DESCRIBE \
  --resource '{"Table": {"DatabaseName": "reporting_db", "Name": "finance_transactions_link", "CatalogId": "123456789012"}}'
```

Your resource link should be accessible.
