# End-to-End Example: RDS Proxy Deployment

A walkthrough showing how to use the `rds-proxy-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an RDS Proxy for an Aurora PostgreSQL cluster
with IAM authentication, TLS enforcement, Secrets Manager integration
with rotation, and multi-AZ deployment. The proxy needs:

- Proxy name: my-app-proxy
- Target: Aurora PostgreSQL cluster my-aurora-cluster
- Engine: POSTGRESQL
- IAM authentication: enabled
- TLS: required
- Secrets Manager secret: rds/db-credentials-abc (with rotation)
- IAM role: rds-proxy-role
- Subnet group: 3 AZs (us-east-1a, us-east-1b, us-east-1c)
- Proxy SG: sg-proxy111
- Database SG: sg-database222 (ingress from proxy SG on port 5432)
- Max connections: 75%
- Max idle connections: 50%
- Region: us-east-1
- Account: 123456789012

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-rds-proxy
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an RDS Proxy for my Aurora PostgreSQL cluster
      with IAM auth, TLS, and Secrets Manager rotation.
      Multi-AZ across us-east-1a, 1b, 1c."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an rds proxy"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
RDS_PROXY: my-app-proxy (my-app-proxy.proxy-abc123.us-east-1.rds.amazonaws.com)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Proxy name: my-app-proxy
  [✓] Engine family: POSTGRESQL
  [✓] Target: my-aurora-cluster (cluster)
  [✓] Secrets Manager secret: format verified (username, password, engine, host, port, dbClusterIdentifier)
  [✓] IAM role: rds-proxy-role (trusts rds.amazonaws.com, has secretsmanager:GetSecretValue)
  [✓] Secrets Manager rotation: enabled (30 days)
  [✓] IAM authentication: ENABLED (requires TLS)
  [✓] TLS/SSL: required
  [✓] DB subnet group: my-proxy-subnet-group (3 AZs: us-east-1a, us-east-1b, us-east-1c)
  [✓] Security group (proxy): sg-proxy111
  [✓] Security group (database → proxy ingress): ALLOWED on port 5432
  [✓] Max connections percent: 75%
  [✓] Max idle connections percent: 50%
  [✓] Multi-AZ: YES (subnets span 3 AZs)
  [✓] Proxy endpoint: my-app-proxy.proxy-abc123.us-east-1.rds.amazonaws.com
  [✓] Tags: Environment=production
VERIFICATION_COMMANDS:
  aws rds describe-db-proxies --db-proxy-name my-app-proxy --region us-east-1
  aws secretsmanager get-secret-value --secret-id rds/db-credentials-abc --region us-east-1
  aws rds describe-db-proxy-target-groups --db-proxy-name my-app-proxy --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the IAM role for the proxy
aws iam create-role \
  --role-name "rds-proxy-role" \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"rds.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy \
  --role-name "rds-proxy-role" \
  --policy-name "secrets-access" \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"secretsmanager:GetSecretValue","Resource":"arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-*"}]}'

# Step 2: Create the DB subnet group (3 AZs)
aws rds create-db-subnet-group \
  --db-subnet-group-name "my-proxy-subnet-group" \
  --db-subnet-group-description "Subnet group for RDS Proxy" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc

# Step 3: Create the proxy security group
PROXY_SG=$(aws ec2 create-security-group \
  --group-name "rds-proxy-sg" --description "RDS Proxy SG" \
  --vpc-id vpc-aaa11122 --query 'GroupId' --output text)

# Step 4: Allow ingress from proxy SG to database SG (CRITICAL)
aws ec2 authorize-security-group-ingress \
  --group-id sg-database222 --protocol tcp --port 5432 \
  --source-security-group-id "$PROXY_SG"

# Step 5: Create the proxy
aws rds create-db-proxy \
  --db-proxy-name "my-app-proxy" \
  --engine-family POSTGRESQL \
  --auth '[{"AuthScheme":"SECRETS","SecretArn":"arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc","IAMAuth":"ENABLED"}]' \
  --role-arn "arn:aws:iam::123456789012:role/rds-proxy-role" \
  --vpc-subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --vpc-security-group-ids "$PROXY_SG" \
  --require-tls

# Step 6: Configure the target group with max connections
aws rds create-db-proxy-target-group \
  --db-proxy-name "my-app-proxy" \
  --target-group-name "default" \
  --connection-pool-config '{"MaxConnectionsPercent":75,"MaxIdleConnectionsPercent":50}'

# Step 7: Associate the Aurora cluster target
aws rds create-db-proxy-target \
  --db-proxy-name "my-app-proxy" \
  --target-group-name "default" \
  --db-cluster-identifier "my-aurora-cluster"

# Step 8: Enable Secrets Manager rotation
aws secretsmanager rotate-secret \
  --secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc" \
  --rotation-lambda-arn "arn:aws:lambda:us-east-1:123456789012:function:secretsmanager-rds-rotation" \
  --rotation-rules '{"AutomaticallyAfterDays":30}'
```

---

## Step 4 — Post-deployment verification

```bash
# Proxy status — should be Available
aws rds describe-db-proxies \
  --db-proxy-name my-app-proxy \
  --query 'DBProxies[0].Status' --region us-east-1

# Target group connection pool config
aws rds describe-db-proxy-target-groups \
  --db-proxy-name my-app-proxy --region us-east-1

# Target association
aws rds describe-db-proxy-targets \
  --db-proxy-name my-app-proxy --region us-east-1

# Secret format verification
aws secretsmanager get-secret-value \
  --secret-id rds/db-credentials-abc \
  --query 'SecretString' --output text --region us-east-1 | jq .
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Proxy endpoint | Points app at cluster endpoint | Explicit proxy endpoint | Using cluster endpoint bypasses the proxy entirely |
| Secret format | Does not verify | Verifies JSON keys | Wrong format causes Unavailable status |
| MaxConnectionsPercent | Set at proxy level (wrong) | Set on target group | The parameter belongs on the target group |
| DB SG ingress | Forgotten | Proxy SG → DB SG rule | Without it, connections time out |
| IAM auth + TLS coupling | IAM auth without TLS | IAM auth requires TLS | IAM auth fails without TLS |
| Subnet group | Single-AZ subnets | Verifies 2+ AZs | Single-AZ proxy is not highly available |
| Secrets Manager rotation | Static secret | Rotation pairing | Rotation eliminates credential downtime |
| Failover | Not considered | Proxy reroutes on failover | Key proxy benefit for Aurora |

---

## Related artifacts

- **Skill definition:** `skills/rds-proxy-deployer/SKILL.md`
- **Secrets and IAM auth guide:** `skills/rds-proxy-deployer/references/secrets-and-iam-auth.md`
- **Subnet and sizing guide:** `skills/rds-proxy-deployer/references/subnet-and-sizing.md`
- **Slash command:** `commands/aws/deploy-rds-proxy.md`
- **Eval suite:** `skills/rds-proxy-deployer/evals/evals.json`
- **Legacy test cases:** `skills/rds-proxy-deployer/eval/test-cases.yaml`
