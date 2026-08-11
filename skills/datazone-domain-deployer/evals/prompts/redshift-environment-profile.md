# Eval: redshift-environment-profile

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Redshift data source, Default Data Warehouse blueprint, environment profile targeting specific account and region

## Prompt

Create a DataZone domain called dw-domain in us-east-1, account
111111111111. Project sales-analytics. Add a Redshift data source
sales-dw-cluster, database sales_db, in account 222222222222.
Redshift credentials in Secrets Manager secret
arn:aws:secretsmanager:us-east-1:222222222222:secret:redshift-creds.
Source account IAM role DataZoneRedshiftAccessRole. Enable the
Default Data Warehouse blueprint. Create an environment profile
production-dw targeting account 222222222222, region us-east-1.
Tags: Environment=production, Blueprint=data-warehouse.
