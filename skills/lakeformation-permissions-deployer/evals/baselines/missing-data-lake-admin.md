# Baseline (no-skill) — missing-data-lake-admin

> This is the response a model produces **without** the skill definition.
> It proceeds with LF-tag creation and permission grants without flagging
> that no data lake admin is registered. All Lake Formation API calls fail
> with `AccessDeniedException` because only registered admins can create
> LF-tags and grant permissions.

---

Here are the commands to deploy your Lake Formation LF-tag based
access control:

```bash
aws lakeformation create-lf-tag \
  --tag-key environment \
  --tag-values production staging

aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"}' \
  --permissions SELECT \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}]}}'
```

Your permissions should be applied.
