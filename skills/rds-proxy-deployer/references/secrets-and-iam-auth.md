# Secrets Manager and IAM Authentication — RDS Proxy Deployer

Deep reference on Secrets Manager secret format for RDS Proxy, IAM role
configuration, Secrets Manager rotation pairing, IAM database
authentication with tokens, and the TLS requirement for IAM auth. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Secrets Manager secret format for RDS Proxy

### Required JSON structure

The Secrets Manager secret referenced by the RDS Proxy MUST contain a
JSON object with the following keys:

```json
{
  "username": "admin",
  "password": "secret-password-here",
  "engine": "postgres",
  "host": "my-aurora-cluster.cluster-abc.us-east-1.rds.amazonaws.com",
  "port": 5432,
  "dbClusterIdentifier": "my-aurora-cluster"
}
```

For RDS instances (not Aurora clusters), use `dbInstanceIdentifier`
instead of `dbClusterIdentifier`.

### Verify the secret format

```bash
aws secretsmanager get-secret-value \
  --secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc" \
  --query 'SecretString' --output text --region us-east-1 | jq .

# Verify required keys are present
aws secretsmanager get-secret-value \
  --secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc" \
  --query 'SecretString' --output text --region us-east-1 | \
  jq 'has("username") and has("password") and has("engine") and has("host") and has("port")'
# → true
```

### Common secret format mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Missing `dbClusterIdentifier` | Proxy health checks fail | Add the cluster identifier to the JSON |
| Wrong `engine` value | Proxy cannot connect | Use `postgres` or `mysql` (not `postgresql` or `aurora-postgresql`) |
| Wrong `host` value | Proxy connects to wrong endpoint | Use the cluster endpoint, not a custom hostname |
| Missing `port` | Proxy uses default port (may be wrong) | Explicitly include the port (5432 or 3306) |
| Plain-text password (not JSON) | Proxy cannot parse credentials | Store as a JSON object, not a plain string |

## IAM role for the proxy

### Trust policy

The role must trust `rds.amazonaws.com`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "rds.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

### Permission policy

The role must have `secretsmanager:GetSecretValue` on the secret(s):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-*"
  }]
}
```

### Creating the role via CLI

```bash
# Create the trust policy document
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "rds.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create the role
aws iam create-role \
  --role-name "rds-proxy-role" \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --region us-east-1

# Attach the permissions policy
cat > /tmp/permissions-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-*"
  }]
}
EOF

aws iam put-role-policy \
  --role-name "rds-proxy-role" \
  --policy-name "rds-proxy-secrets-access" \
  --policy-document file:///tmp/permissions-policy.json \
  --region us-east-1
```

## Secrets Manager rotation pairing

### Why rotation matters

Without rotation, the database credentials in the secret are static.
When an administrator changes the database password, the secret becomes
out of sync and the proxy fails to connect.

With rotation, Secrets Manager periodically updates the password in BOTH
the secret and the database. The RDS Proxy automatically picks up the
new credentials without dropping connections.

### Enable rotation

```bash
aws secretsmanager rotate-secret \
  --secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc" \
  --rotation-lambda-arn "arn:aws:lambda:us-east-1:123456789012:function:secretsmanager-rds-rotation" \
  --rotation-rules '{"AutomaticallyAfterDays":30}' \
  --region us-east-1
```

### Rotation Lambda

AWS provides a managed rotation Lambda template for RDS credentials.
The Lambda function:
1. Generates a new password.
2. Connects to the database and changes the password.
3. Updates the secret in Secrets Manager.
4. The RDS Proxy detects the new secret version and picks up the new
   credentials transparently.

The rotation Lambda's IAM role needs:
- `secretsmanager:GetSecretValue` and `secretsmanager:PutSecretValue`
  on the secret.
- `rds-db:connect` on the database (or the database admin credentials).

## IAM database authentication

### How IAM auth works with RDS Proxy

IAM database authentication allows applications to authenticate to the
database using a short-lived IAM token instead of a password. The token
is generated by the AWS SigV4 signer and is valid for 15 minutes.

```bash
# Generate an IAM auth token
TOKEN=$(aws rds generate-db-auth-token \
  --hostname "my-app-proxy.proxy-abc123.us-east-1.rds.amazonaws.com" \
  --port 5432 \
  --region us-east-1 \
  --username "iam-db-user")
```

### IAM auth + TLS coupling

IAM auth REQUIRES TLS. The token is sent as the "password" in the
database authentication handshake. Without TLS, the token is
interceptable. The proxy MUST be created with `--require-tls` for IAM
auth to work.

```bash
aws rds create-db-proxy \
  --db-proxy-name "my-app-proxy" \
  --auth '[{"AuthScheme":"SECRETS","SecretArn":"...","IAMAuth":"ENABLED"}]' \
  --require-tls \
  ...
```

### IAM policy for application database access

The application's IAM role needs `rds-db:connect` on the proxy:

```json
{
  "Effect": "Allow",
  "Action": "rds-db:connect",
  "Resource": "arn:aws:rds-db:us-east-1:123456789012:dbproxy:prx-abc123/*"
}
```

### When to use IAM auth vs password auth

| Factor | IAM auth | Password auth |
|---|---|---|
| Credential rotation | Automatic (token expires in 15 min) | Manual or via Secrets Manager rotation |
| Network requirement | TLS required | TLS optional |
| Application complexity | Must generate tokens | Use password from secret |
| Best for | Serverless (Lambda, Fargate), short-lived compute | Long-running applications, legacy systems |

## Terraform examples

```hcl
# IAM role for RDS Proxy
resource "aws_iam_role" "rds_proxy" {
  name = "rds-proxy-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "rds.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "rds_proxy_secrets" {
  name = "rds-proxy-secrets-access"
  role = aws_iam_role.rds_proxy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.db_credentials.arn
    }]
  })
}

# RDS Proxy
resource "aws_db_proxy" "main" {
  name = "my-app-proxy"
  engine_family = "POSTGRESQL"
  role_arn = aws_iam_role.rds_proxy.arn
  require_tls = true

  auth {
    auth_scheme = "SECRETS"
    iam_auth = "ENABLED"
    secret_arn = aws_secretsmanager_secret.db_credentials.arn
  }

  vpc_subnet_ids = aws_subnet.proxy[*].id
  vpc_security_group_ids = [aws_security_group.proxy.id]
}

# Secrets Manager rotation
resource "aws_secretsmanager_secret_rotation" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  rotation_lambda_arn = aws_lambda_function.rotation.arn

  rotation_rules {
    automatically_after_days = 30
  }
}
```

## Expert heuristic: Secrets Manager rotation pairing

The secret used by the proxy should be the SAME secret managed by
Secrets Manager rotation. When the secret rotates, the proxy
automatically picks up new credentials without dropping connections.

```text
Secrets Manager rotation lifecycle:
  1. Secret stored (JSON: username, password, engine, host, port, dbClusterIdentifier)
  2. RDS Proxy references secret ARN → assumes IAM role → reads secret
  3. Rotation Lambda fires → new password in DB → updates secret
  4. RDS Proxy detects secret version change → picks up new credentials
     → no connection drops, no application downtime
```

**Key implication:** pairing rotation with RDS Proxy eliminates the
"credential rotation causes downtime" problem. The proxy handles
rotation transparently.
