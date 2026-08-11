# Baseline (no-skill) — missing-lf-tag-on-resource

> This is the response a model produces **without** the skill definition.
> It creates LF-tag keys, attaches tags to the database, and grants the
> LF-tag-based permission — but does not verify that LF-tags are attached
> to the target table. The grant matches nothing (the table has no
> LF-tags), and the principal silently receives zero access.

---

Here are the commands to deploy your Lake Formation LF-tag based
access control:

```bash
aws lakeformation create-lf-tag \
  --tag-key environment \
  --tag-values production staging

aws lakeformation add-lf-tags-to-resource \
  --resource '{"Database": {"Name": "analytics_db"}}' \
  --lf-tags '[{"TagKey": "environment", "TagValues": ["production"]}]'

aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"}' \
  --permissions SELECT \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]}}'
```

Your permissions should be applied.
