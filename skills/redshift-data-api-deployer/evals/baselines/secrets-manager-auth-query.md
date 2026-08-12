# Baseline (no-skill) — secrets-manager-auth-query

> This is the response a model produces **without** the skill
> definition. It provides a basic Lambda function but omits the
> secretsmanager:GetSecretValue IAM permission, does not handle the
> 24-hour result expiry, has no abort plan, does not set up result
> persistence to DynamoDB, and misses the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create a Lambda function that queries Redshift:

```python
import boto3

client = boto3.client('redshift-data')

def lambda_handler(event, context):
    resp = client.execute_statement(
        ClusterIdentifier='my-redshift-cluster',
        SecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx',
        Database='dev',
        Sql="SELECT COUNT(*) FROM sales WHERE sale_date >= '2026-01-01'"
    )
    return resp
```

The Lambda role just needs redshift-data:ExecuteStatement.
