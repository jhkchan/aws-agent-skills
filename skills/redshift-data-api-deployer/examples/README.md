# End-to-End Example: Redshift Data API Deployment

A walkthrough showing how to use the `redshift-data-api-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a Lambda function that queries Redshift via the Data
API using Secrets Manager authentication. The integration needs:

- Cluster: my-redshift-cluster
- Database: dev
- Auth: Secrets Manager (arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx)
- Lambda: sales-query
- SQL: SELECT COUNT(*) FROM sales WHERE sale_date >= '2026-01-01'
- Poll: every 2 seconds
- Result persistence: write to DynamoDB immediately
- Tags: Environment=production, Workflow=sales-counter

---

## Step 1 — Invoke the skill

### Option A: Natural language

```
You: "Create a Redshift Data API configuration for querying the
      sales table on cluster my-redshift-cluster. Use Secrets
      Manager for auth. Lambda function sales-query. Poll every
      2 seconds. Persist results to DynamoDB."
```

### Option B: CLI routing

```bash
node cli/bin/cli.js route "redshift data api lambda query"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
DATA_API: my-redshift-cluster (SECRET_ARN)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Cluster/Workgroup: my-redshift-cluster (exists, available)
  [✓] Database: dev
  [✓] Authentication: SecretArn
  [✓] Secret ARN: arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx
  [✓] IAM role: redshift-data:ExecuteStatement, DescribeStatement, GetStatementResult
  [✓] IAM role: secretsmanager:GetSecretValue on redshift-creds-xxx
  [✓] SQL: SELECT COUNT(*) FROM sales WHERE sale_date >= '2026-01-01'
  [✓] Result handling: immediate retrieval + write to DynamoDB
  [✓] 24-hour result expiry: results persisted to DynamoDB within 1 minute of FINISHED
  [✓] Polling pattern: Lambda poll (interval 2s, max 60 iterations)
  [✓] Abort plan: AbortStatement if poll exceeds 60 iterations
  [✓] CloudTrail audit: enabled (SQL text logged)
  [✓] Tags: Environment=production, Workflow=sales-counter
VERIFICATION_COMMANDS:
  aws redshift-data describe-statement --id <statement-id>
  aws redshift-data get-statement-result --id <statement-id>
  aws redshift-data list-statements --status FINISHED --max-results 10
```

---

## Step 3 — Lambda function implementation

```python
import boto3
import time
import os

redshift_data = boto3.client('redshift-data')
dynamodb = boto3.resource('dynamodb')

CLUSTER_ID = os.environ['REDSHIFT_CLUSTER_ID']
SECRET_ARN = os.environ['REDSHIFT_SECRET_ARN']
DATABASE = os.environ['REDSHIFT_DATABASE']
TABLE_NAME = os.environ['DYNAMODB_TABLE']

SQL = "SELECT COUNT(*) FROM sales WHERE sale_date >= '2026-01-01'"
POLL_INTERVAL = 2  # seconds
MAX_POLLS = 60     # 120 seconds max

def lambda_handler(event, context):
    # Step 1: Submit the query
    response = redshift_data.execute_statement(
        ClusterIdentifier=CLUSTER_ID,
        SecretArn=SECRET_ARN,
        Database=DATABASE,
        Sql=SQL,
        StatementName='sales-counter'
    )
    statement_id = response['Id']
    
    # Step 2: Poll for completion
    for i in range(MAX_POLLS):
        desc = redshift_data.describe_statement(Id=statement_id)
        status = desc['Status']
        
        if status == 'FINISHED':
            # Step 3: Retrieve results
            result = redshift_data.get_statement_result(Id=statement_id)
            count = result['Records'][0][0]['longValue']
            
            # Step 4: Persist to DynamoDB (before 24-hour expiry)
            table = dynamodb.Table(TABLE_NAME)
            table.put_item(Item={
                'query_id': statement_id,
                'sale_count': count,
                'timestamp': int(time.time())
            })
            
            return {'statusCode': 200, 'count': count}
        
        elif status in ('FAILED', 'ABORTED'):
            error = desc.get('Error', 'Unknown')
            raise Exception(f"Query {status}: {error}")
        
        time.sleep(POLL_INTERVAL)
    
    # Step 5: Timeout — abort the statement
    redshift_data.abort_statement(StatementId=statement_id)
    raise TimeoutError(f"Query timed out after {MAX_POLLS * POLL_INTERVAL}s")
```

---

## Step 4 — IAM policy for the Lambda execution role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:AbortStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/query-results"
    }
  ]
}
```

---

## Step 5 — Deploy and verify

```bash
# Deploy the Lambda function
aws lambda create-function \
  --function-name sales-query \
  --runtime python3.12 \
  --handler index.lambda_handler \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::123456789012:role/RedshiftDataQueryRole \
  --timeout 120 \
  --environment Variables='{
    REDSHIFT_CLUSTER_ID=my-redshift-cluster,
    REDSHIFT_SECRET_ARN=arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx,
    REDSHIFT_DATABASE=dev,
    DYNAMODB_TABLE=query-results
  }'

# Invoke the function
aws lambda invoke \
  --function-name sales-query \
  --payload '{}' \
  response.json

# Verify the statement in CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=redshift-data.amazonaws.com \
  --max-results 10
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| secretsmanager:GetSecretValue | Missing | Added to IAM policy | Without it, ExecuteStatement fails with AccessDenied |
| 24-hour result expiry | Not handled | DynamoDB persistence immediately | Results expire; must persist before 24h |
| AbortStatement | Not configured | Abort on timeout | Prevents orphaned queries consuming cluster resources |
| Poll rate limit | Not considered | 2s interval | 1/s rate limit per statement; too fast causes throttling |
| DescribeStatement before GetStatementResult | Not checked | Status check first | GetStatementResult fails if not FINISHED |
| BatchExecuteStatement transactionality | Assumed transactional | Noted as non-transactional | Statements run sequentially; no automatic rollback |

---

## Related artifacts

- **Skill definition:** `skills/redshift-data-api-deployer/SKILL.md`
- **Authentication and Secrets guide:** `skills/redshift-data-api-deployer/references/authentication-and-secrets.md`
- **Statement Lifecycle and Results guide:** `skills/redshift-data-api-deployer/references/statement-lifecycle-and-results.md`
- **Eval suite:** `skills/redshift-data-api-deployer/evals/evals.json`
- **Legacy test cases:** `skills/redshift-data-api-deployer/eval/test-cases.yaml`
