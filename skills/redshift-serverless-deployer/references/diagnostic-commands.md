# Diagnostic Commands — Redshift Serverless Deployer

Step 11 post-deployment verification command listing moved verbatim from SKILL.md. Loaded on demand.

## Step 11 — verification commands

```bash
aws redshift-serverless describe-workgroup --workgroup-name analytics-wg-prod
aws redshift-serverless describe-namespace --namespace-name analytics-ns-prod
aws redshift-serverless list-usage-limits
aws redshift-serverless describe-scheduled-actions
aws secretsmanager describe-secret --secret-id redshift/admin
aws kms describe-key --key-id alias/redshift-prod
aws logs describe-log-groups --log-group-name-prefix /aws/redshift/analytics-ns-prod
```
