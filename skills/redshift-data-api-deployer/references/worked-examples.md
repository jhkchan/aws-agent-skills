# Worked Examples — Redshift Data API Deployer

Lambda polling and EventBridge notification implementation patterns moved verbatim from SKILL.md. Loaded on demand.

## Pattern 1 — Lambda polling (full code)

```python
import boto3
import time

redshift_data = boto3.client('redshift-data')

def lambda_handler(event, context):
    # Submit the query
    response = redshift_data.execute_statement(
        ClusterIdentifier='my-redshift-cluster',
        SecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx',
        Database='dev',
        Sql='SELECT COUNT(*) FROM sales'
    )
    statement_id = response['Id']
    
    # Poll for completion
    while True:
        desc = redshift_data.describe_statement(Id=statement_id)
        status = desc['Status']
        
        if status == 'FINISHED':
            result = redshift_data.get_statement_result(Id=statement_id)
            return { 'rows': result['Records'] }
        elif status in ('FAILED', 'ABORTED'):
            raise Exception(f"Query {status}: {desc.get('Error', 'Unknown')}")
        
        time.sleep(1)  # Poll interval
```

## Pattern 2 — EventBridge notification (full code)

```python
# Step 1: Submit query with WithEvent=True
response = redshift_data.execute_statement(
    ClusterIdentifier='my-redshift-cluster',
    SecretArn='arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx',
    Database='dev',
    Sql='SELECT COUNT(*) FROM sales',
    WithEvent=True  # Emit EventBridge on completion
)
return { 'statementId': response['Id'] }

# Step 2: EventBridge rule triggers target Lambda
# Event pattern: { "source": ["aws.redshift-data"], "detail-type": ["Redshift Data Statement Status Change"] }
def result_handler(event, context):
    statement_id = event['detail']['statementId']
    status = event['detail']['status']
    
    if status == 'FINISHED':
        result = redshift_data.get_statement_result(Id=statement_id)
        return { 'rows': result['Records'] }
```
