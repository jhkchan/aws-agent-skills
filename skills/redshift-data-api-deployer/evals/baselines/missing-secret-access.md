# Baseline (no-skill) — missing-secret-access

> This is the response a model produces **without** the skill
> definition. It creates the Lambda function without flagging the
> missing secretsmanager:GetSecretValue IAM permission as a
> prerequisite gap. The Lambda would fail at runtime with
> AccessDenied. Generated for with-skill-vs-baseline comparison.

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
        Sql='SELECT 1'
    )
    return resp
```

The Lambda role has redshift-data:ExecuteStatement so it should work.
