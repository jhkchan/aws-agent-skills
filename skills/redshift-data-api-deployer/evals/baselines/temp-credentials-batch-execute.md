# Baseline (no-skill) — temp-credentials-batch-execute

> This is the response a model produces **without** the skill
> definition. It uses batch_execute_statement but does not explain
> the sequential non-transactional nature, omits the
> GetClusterCredentials call, does not note AutoCreate semantics,
> and misses the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create a batch execution:

```python
import boto3

client = boto3.client('redshift-data')

response = client.batch_execute_statement(
    ClusterIdentifier='analytics-cluster',
    Database='reports',
    DbUser='iam_report_user',
    Sqls=[
        'CREATE TEMP TABLE temp_sales AS SELECT * FROM sales',
        'SELECT COUNT(*) FROM temp_sales',
        'DROP TABLE temp_sales'
    ]
)
```

That should work.
