# Baseline (no-skill) — missing-workspace-role-permissions

> This is the response a model produces **without** the skill
> definition. It creates the workspace and data source without
> flagging that the workspace IAM role is missing critical
> cloudwatch:GetMetricData, GetMetricStatistics, and logs:StartQuery
> permissions. The CloudWatch data source would silently return empty
> results. Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here's the workspace:

```bash
aws grafana create-workspace \
  --workspace-name prod-grafana \
  --authentication-provider AWS_SSO \
  --data-sources CLOUDWATCH \
  --workspace-role-arn arn:aws:iam::123456789012:role/GrafanaWorkspaceRole
```

The CloudWatch data source should work with the workspace role.
