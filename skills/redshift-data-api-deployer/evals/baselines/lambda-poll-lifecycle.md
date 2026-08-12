# Baseline (no-skill) — lambda-poll-lifecycle

> This is the response a model produces **without** the skill
> definition. It provides a basic Lambda poll loop but has no abort
> plan for timeout, does not handle the 24-hour result expiry, uses
> no polling rate limit awareness, and misses the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create a Lambda that polls:

```python
import boto3
import time

client = boto3.client('redshift-data')

def lambda_handler(event, context):
    resp = client.execute_statement(
        ClusterIdentifier='data-warehouse',
        SecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:dw-creds',
        Database='production',
        Sql='SELECT ... long aggregation ...'
    )
    stmt_id = resp['Id']
    
    while True:
        desc = client.describe_statement(Id=stmt_id)
        if desc['Status'] == 'FINISHED':
            return client.get_statement_result(Id=stmt_id)
        time.sleep(3)
```

Just keep polling until it finishes.
