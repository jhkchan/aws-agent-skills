# Authentication and Secrets — Redshift Data API Deployer

Deep reference on Data API authentication methods (Secrets Manager
vs temporary credentials), Secrets Manager secret structure for
Redshift, GetClusterCredentials mechanics, IAM permissions, and
credential rotation. Loaded on demand by the skill — kept out of
the main SKILL.md body so the deployment procedure stays scannable.

## Authentication methods overview

The Data API supports two authentication methods. Each
ExecuteStatement call uses exactly ONE — they are mutually exclusive.

| Method | Parameter | How it works |
|---|---|---|
| Secrets Manager | `SecretArn` | Secret contains DB credentials; Data API reads the secret at query time |
| Temp credentials | `DbUser` | Data API calls GetClusterCredentials internally to generate short-lived creds |

## Secrets Manager authentication

### Secret structure

The secret must be a JSON object with Redshift connection fields:

```json
{
  "username": "admin",
  "password": "MySecurePassword123!",
  "engine": "redshift",
  "host": "my-redshift-cluster.abc123.us-east-1.redshift.amazonaws.com",
  "port": 5439,
  "dbClusterIdentifier": "my-redshift-cluster"
}
```

### Creating the secret

```bash
aws secretsmanager create-secret \
  --name redshift/my-redshift-cluster \
  --secret-string '{
    "username": "admin",
    "password": "MySecurePassword123!",
    "engine": "redshift",
    "host": "my-redshift-cluster.abc123.us-east-1.redshift.amazonaws.com",
    "port": 5439,
    "dbClusterIdentifier": "my-redshift-cluster"
  }'
```

### Using the secret with Data API

```bash
aws redshift-data execute-statement \
  --cluster-identifier my-redshift-cluster \
  --secret-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift/my-redshift-cluster-xxx \
  --database dev \
  --sql "SELECT * FROM sales LIMIT 10"
```

### IAM permissions

The Lambda/caller execution role needs:

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
        "redshift-data:BatchExecuteStatement",
        "redshift-data:ListStatements",
        "redshift-data:AbortStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift/my-redshift-cluster-*"
    }
  ]
}
```

### Credential rotation

Secrets Manager supports automatic rotation via Lambda rotation
functions. For Redshift, AWS provides a managed rotation template.

```bash
# Enable rotation (rotates every 30 days)
aws secretsmanager rotate-secret \
  --secret-id redshift/my-redshift-cluster \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:RedshiftRotation \
  --rotation-rules AutomaticallyAfterDays=30
```

**Key implication:** when rotation is enabled, the Data API always
reads the latest secret value at query time. No application code
changes are needed when the password rotates.

## Temporary credentials authentication

### How GetClusterCredentials works

GetClusterCredentials generates short-lived database credentials for
an IAM principal. The credentials are mapped to a Redshift database
user.

```bash
aws redshift get-cluster-credentials \
  --cluster-identifier my-redshift-cluster \
  --db-user iam_user \
  --db-name dev \
  --duration-seconds 3600 \
  --auto-create false
```

Returns:
```json
{
  "DbUser": "IAM:iam_user",
  "DbPassword": "temporary-generated-password",
  "Expiration": "2026-08-11T01:00:00Z"
}
```

### Using with Data API

When you pass `DbUser` (without `SecretArn`) to ExecuteStatement,
the Data API internally calls GetClusterCredentials.

```bash
aws redshift-data execute-statement \
  --cluster-identifier my-redshift-cluster \
  --db-user iam_user \
  --database dev \
  --sql "SELECT * FROM sales LIMIT 10"
```

### AutoCreate option

When `AutoCreate` is true, Redshift automatically creates a database
user matching the IAM principal if it does not exist.

```text
AutoCreate: true
  → IAM user "alice" → Redshift user "IAM:alice" auto-created
  → Useful for IAM-federated access without pre-provisioning users

AutoCreate: false (default)
  → The DbUser must already exist in Redshift
  → If not found, GetClusterCredentials fails
```

### DbGroups

You can map IAM users to Redshift database groups:

```bash
aws redshift get-cluster-credentials \
  --cluster-identifier my-redshift-cluster \
  --db-user iam_user \
  --db-name dev \
  --db-groups "analyst_group" "readonly_group" \
  --auto-create true
```

### IAM permissions for temp credentials

The Lambda/caller role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "redshift:GetClusterCredentials",
      "Resource": "*"
    }
  ]
}
```

## Comparison: Secrets Manager vs temp credentials

| Factor | Secrets Manager | Temp Credentials |
|---|---|---|
| Setup complexity | Create secret + rotation function | IAM policy only |
| Password in code | No | No |
| Credential rotation | Automatic (Secrets Manager) | N/A (auto-generated, short-lived) |
| Per-user IAM mapping | No (shared secret) | Yes (AutoCreate maps IAM to DB user) |
| Cost | $0.40/secret/month | Free |
| Caching benefit | Secret read every call | Creds valid for DurationSeconds |
| Best for | Centralized production | IAM-federated, per-user access |

## Caching temp credentials in Lambda

To reduce API calls, cache temp credentials across Lambda invocations
within the same execution context:

```python
import boto3
import time

_client = boto3.client('redshift')
_cached_creds = None
_creds_expiry = 0

def get_cached_creds():
    global _cached_creds, _creds_expiry
    
    if _cached_creds and time.time() < _creds_expiry - 60:  # 60s buffer
        return _cached_creds
    
    resp = _client.get_cluster_credentials(
        ClusterIdentifier='my-redshift-cluster',
        DbUser='iam_user',
        DbName='dev',
        DurationSeconds=3600
    )
    _cached_creds = resp
    _creds_expiry = time.time() + 3600
    return resp
```

This avoids calling GetClusterCredentials on every Lambda invocation
when the cached credentials are still valid.

## Common authentication pitfalls

### Pitfall 1: Missing secretsmanager:GetSecretValue

The Lambda role has redshift-data:ExecuteStatement but NOT
secretsmanager:GetSecretValue. ExecuteStatement fails with
"AccessDenied" when trying to read the secret.

**Fix:** add secretsmanager:GetSecretValue on the secret ARN to the
Lambda execution role.

### Pitfall 2: Expired temp credentials

Temp credentials expire after DurationSeconds. If a Lambda caches
creds and reuses them after expiry, queries fail.

**Fix:** check expiration before reuse, and re-call
GetClusterCredentials when expired.

### Pitfall 3: AutoCreate with existing user

AutoCreate: true when the user already exists is fine — Redshift
recognizes the existing user. But if the existing user has different
permissions than the DbGroups specified, the groups are NOT applied
to the existing user.

**Fix:** manage DB user permissions explicitly, or use DbGroups with
AutoCreate: false.

### Pitfall 4: Secret with wrong engine type

The secret must have `"engine": "redshift"`. If the engine field is
missing or wrong, the Data API may fail to parse the secret.

**Fix:** verify the secret structure matches the Redshift secret format.

## Step 2 — auth code samples (Secrets Manager + temp credentials) (from SKILL.md)

**Secrets Manager auth:**

```bash
aws redshift-data execute-statement \
  --cluster-identifier my-redshift-cluster \
  --secret-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds-xxx \
  --database dev \
  --sql "SELECT * FROM sales LIMIT 10" \
  --statement-name "query-sales"
```

**Temp credentials auth:**

```bash
# Step 1: Get temp credentials
CREDS=$(aws redshift get-cluster-credentials \
  --cluster-identifier my-redshift-cluster \
  --db-user my_iam_user \
  --db-name dev \
  --duration-seconds 3600)

DB_USER=$(echo "$CREDS" | jq -r '.DbUser')
DB_PASSWORD=$(echo "$CREDS" | jq -r '.DbPassword')

# Step 2: Use temp creds with Data API (via DbUser parameter)
aws redshift-data execute-statement \
  --cluster-identifier my-redshift-cluster \
  --db-user "$DB_USER" \
  --database dev \
  --sql "SELECT * FROM sales LIMIT 10"
```
