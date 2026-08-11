# Baseline (no-skill) — lf-tag-based-access

> This is the response a model produces **without** the skill definition.
> It creates LF-tags and grants permissions but skips data lake admin
> registration verification, does not attach LF-tags to resources before
> granting (causing silent zero-access), and grants table-level SELECT
> instead of LF-tag-based grants. The principal receives zero access
> because tag-based grants match nothing without LF-tags on resources.

---

Here are the commands to deploy your Lake Formation LF-tag based
access control:

```bash
aws lakeformation create-lf-tag \
  --tag-key environment \
  --tag-values production staging dev

aws lakeformation create-lf-tag \
  --tag-key department \
  --tag-values finance engineering marketing

aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"}' \
  --permissions SELECT DESCRIBE \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]}}'
```

Your permissions should be applied.
