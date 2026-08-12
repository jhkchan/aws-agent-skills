# Baseline (no-skill) — statement-result-pagination

> This is the response a model produces **without** the skill
> definition. It calls GetStatementResult once without pagination,
> does not use UNLOAD for large result sets, ignores the 100 MB
> payload limit, and misses the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create a query for the customers table:

```python
import boto3

client = boto3.client('redshift-data')

resp = client.execute_statement(
    ClusterIdentifier='my-redshift-cluster',
    SecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx',
    Database='dev',
    Sql="SELECT * FROM customers WHERE region = 'APAC'"
)
stmt_id = resp['Id']

# Wait for completion...
result = client.get_statement_result(Id=stmt_id)
return result
```

This should return all the rows.
