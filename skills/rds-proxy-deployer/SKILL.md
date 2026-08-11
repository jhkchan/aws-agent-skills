---
name: rds-proxy-deployer
description: >-
  Provisions Amazon RDS Proxy connections with production defaults:
  connection pooling (create-db-proxy), target Aurora cluster or
  serverless v2, Secrets Manager integration for database credentials,
  IAM authentication, TLS/SSL enforcement (require TLS), connection
  target config, security group associations, DB subnet group (multi-AZ),
  max connections percent, max idle connections percent, role alias,
  CloudWatch metrics (DatabaseConnections, CPUUtilization), failover
  handling, Aurora Serverless v2 compatibility, and multi-AZ proxy
  deployment. Emits a READY_TO_DEPLOY checklist with verification
  commands. Use when creating an RDS Proxy, configuring connection
  pooling, setting up Secrets Manager integration, enabling IAM auth,
  or sizing max connections for Aurora. Triggers: create rds proxy,
  rds proxy connection pooling, rds proxy secrets manager, rds proxy
  iam authentication, rds proxy tls, aurora serverless v2 proxy, rds
  proxy multi-az, rds proxy max connections, rds proxy failover.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with rds, secretsmanager,
  iam, ec2, and cloudwatch access. Works with Terraform
  aws_db_proxy / aws_db_proxy_default_target_group /
  aws_db_proxy_target resources and CloudFormation
  AWS::RDS::DBProxy templates.
keywords:
  - aws
  - rds
  - rds proxy
  - aurora
  - connection pooling
  - cloudops
  - deploy
  - provisioning
  - secrets manager
  - iam authentication
  - tls
  - aurora serverless v2
  - multi-az
  - failover
tags:
  - aws
  - rds
  - rds-proxy
  - aurora
  - cloudops
  - deploy
  - databases
  - provisioning
  - connection-pooling
  - secrets-manager
  - iam-auth
  - tls
  - multi-az
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - rds
    - rds-proxy
    - aurora
    - cloudops
    - deploy
    - databases
    - provisioning
    - connection-pooling
    - secrets-manager
    - iam-auth
    - tls
    - multi-az
  dependencies:
    - aws-orchestrator
  keywords:
    - create rds proxy
    - rds proxy connection pooling
    - rds proxy secrets manager
    - rds proxy iam authentication
    - rds proxy tls
    - aurora serverless v2 proxy
    - rds proxy multi-az
    - rds proxy max connections
    - rds proxy failover
  when_to_use: >-
    Invoke when the user wants to create an RDS Proxy for connection
    pooling, configure Secrets Manager integration for database
    credentials, enable IAM authentication, enforce TLS/SSL, size max
    connections based on Aurora ACU, configure a DB subnet group for
    multi-AZ proxy deployment, set up security group associations, wire
    CloudWatch metrics monitoring, handle failover for Aurora clusters,
    or connect the proxy to Aurora Serverless v2. Do NOT invoke for
    auditing existing proxies, RDS instance creation itself, or Aurora
    Global Database configuration.
---

# RDS Proxy Deployer

An AWS CloudOps agent skill that provisions Amazon RDS Proxy
connections with correct defaults. The skill walks the operator through
connection pooling configuration, Secrets Manager integration, IAM
authentication, TLS/SSL enforcement, DB subnet group selection for
multi-AZ, security group associations, max connections sizing based on
Aurora ACU, CloudWatch metrics, failover handling, and Aurora Serverless
v2 compatibility, captures configuration decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist.

## Activation keywords

create RDS Proxy, RDS Proxy connection pooling, RDS Proxy Secrets
Manager, RDS Proxy IAM authentication, RDS Proxy TLS, Aurora Serverless
v2 proxy, RDS Proxy multi-AZ, RDS Proxy max connections, RDS Proxy
failover, RDS Proxy security group.

## STRICT output contract

When this skill is invoked with an RDS-Proxy-provisioning request, the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels `RDS_PROXY:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Connection pooling and target config | Core proxy model |
| Step 2 — Secrets Manager integration | Database credentials |
| Step 3 — IAM authentication | IAM auth setup |
| Step 4 — TLS/SSL enforcement (require TLS) | Encryption in transit |
| Step 5 — DB subnet group and multi-AZ | Network topology |
| Step 6 — Security group associations | Network security |
| Step 7 — Max connections sizing (ACU-based) | Capacity planning |
| Step 8 — CloudWatch metrics and monitoring | Observability |
| Step 9 — Failover handling | Aurora cluster failover |
| Step 10 — Aurora Serverless v2 compatibility | Serverless targets |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/secrets-and-iam-auth.md | Secrets + IAM detail |
| references/subnet-and-sizing.md | Subnet + sizing detail |

## Mindset

**One-line takeaway:** An RDS Proxy sits between your application and
the database, pooling and sharing database connections. Applications
connect to the PROXY ENDPOINT (not the cluster endpoint). The proxy
manages a pool of connections to the underlying Aurora/RDS instances.
Secrets Manager stores the database credentials; the proxy assumes an
IAM role to read them.

Three misconceptions dominate RDS Proxy misconfiguration:

- **"The proxy uses the cluster endpoint."** It does NOT. The proxy has
  its OWN endpoint. Applications must connect to the PROXY endpoint.
  Using the cluster endpoint bypasses the proxy entirely.

- **"Max connections is a fixed number."** It is NOT. RDS Proxy uses
  `MaxConnectionsPercent` — a PERCENTAGE of the target's
  `max_connections` capacity. For Aurora, this depends on instance class
  or ACU (for Serverless v2).

- **"Secrets Manager just needs a secret ARN."** It does not. The secret
  must be in the CORRECT FORMAT: JSON with `username`, `password`,
  `engine`, `host`, `port`, `dbClusterIdentifier`. Wrong format =
  proxy health checks fail.

## Configuration dependency graph (novel heuristic)

RDS Proxy configurations are NOT independent. The proxy requires a DB
subnet group, security groups, Secrets Manager secrets, and an IAM role
before it can be created.

| Configuration | Hard dependencies | Silent failure | Enables |
|---|---|---|---|
| DB subnet group | 2+ subnets in different AZs | single-AZ if subnets in 1 AZ | network placement |
| Secrets Manager secret | correct JSON format | proxy creates but health checks fail if format wrong | database credentials |
| IAM role | trusts `rds.amazonaws.com`; has `secretsmanager:GetSecretValue` | proxy creates but cannot read secrets | secret access |
| RDS Proxy | subnet group, SG, IAM role, secrets all exist | proxy endpoint available but connections fail until target configured | proxy endpoint |
| Proxy target group | proxy exists; target DB exists | `MaxConnectionsPercent` set HERE, not on proxy | connection routing |
| Security groups | proxy SG exists; DB SG allows proxy SG ingress | proxy creates but connections time out if DB SG missing proxy ingress | connectivity |
| IAM auth | proxy created with `--require-tls` and `--auth=IAM` | IAM auth REQUIRES TLS; without TLS, IAM auth fails | token-based auth |

**The secret-format row is the one a baseline model misses.** Creating
the proxy with a secret ARN succeeds even if the secret JSON is wrong.
The proxy enters `Unavailable` status because health checks fail.

## Expert heuristic: proxy endpoint vs cluster endpoint

A baseline model says "create the proxy and point it at the cluster."
The correct heuristic recognizes that the proxy has its OWN endpoint,
and the application connection string must change.

```text
Without RDS Proxy:
  Application → jdbc:postgresql://my-cluster.cluster-abc.rds.amazonaws.com:5432/mydb

With RDS Proxy:
  Application → jdbc:postgresql://my-proxy.proxy-abc123.rds.amazonaws.com:5432/mydb
                    ↑ PROXY endpoint (NOT the cluster endpoint)
  Proxy → pools connections → my-cluster.cluster-abc.rds.amazonaws.com
```

**Key implication:** deploying an RDS Proxy requires an APPLICATION
CHANGE to update the connection string. The proxy provides zero benefit
if the application continues using the cluster endpoint.

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

## Expert heuristic: max connections based on ACU sizing

For Aurora Serverless v2, `max_connections` depends on ACU allocation.
The proxy's `MaxConnectionsPercent` should be sized relative to this.

```text
Aurora Serverless v2 ACU → max_connections (approximate):
  2 ACU → ~90 connections (minimum)
  8 ACU → ~375 connections
  16 ACU → ~750 connections
  64 ACU → ~3,000 connections

RDS Proxy MaxConnectionsPercent:
  ├── Conservative: 90% (leaves 10% for admin/superuser)
  ├── Moderate: 60-75% (good for mixed workloads)
  └── Default: 90%

  Example: 8 ACU (~375 max_connections)
    MaxConnectionsPercent = 75 → proxy manages ~281 connections

  WARNING: setting too high starves admin/monitoring connections.
  Always leave at least 10% headroom.
```

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Aurora cluster or RDS instance exists | Proxy target must exist | `aws rds describe-db-clusters` |
| DB subnet group (2+ AZs) | Proxy requires multi-AZ subnet placement | `aws rds describe-db-subnet-groups` |
| Security group for the proxy | Proxy needs a SG | `aws ec2 describe-security-groups` |
| Database SG allows proxy SG ingress | Without it, connections time out | Verify DB SG ingress rules |
| Secrets Manager secret exists | Proxy reads DB credentials | `aws secretsmanager describe-secret` |
| Secret format correct (JSON keys) | Wrong format = health check failure | `aws secretsmanager get-secret-value` + validate |
| IAM role trusts rds.amazonaws.com | Proxy assumes this role | `aws iam get-role` |
| Role has secretsmanager:GetSecretValue | Without it, proxy cannot read secrets | Check role policies |
| Engine supported (MySQL/PostgreSQL) | Proxy supports these only | Check engine type |

## Step 1 — Connection pooling and target config

```bash
# Create the proxy
PROXY_ID=$(aws rds create-db-proxy \
  --db-proxy-name "my-app-proxy" \
  --engine-family POSTGRESQL \
  --auth '[{"AuthScheme":"SECRETS","SecretArn":"arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc","IAMAuth":"DISABLED"}]' \
  --role-arn "arn:aws:iam::123456789012:role/rds-proxy-role" \
  --vpc-subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --vpc-security-group-ids sg-proxy111 \
  --require-tls \
  --query 'DBProxy.DBProxyName' --output text --region us-east-1)

# Configure target group with max connections (set HERE, not on proxy)
aws rds create-db-proxy-target-group \
  --db-proxy-name "$PROXY_ID" --target-group-name "default" \
  --connection-pool-config '{"MaxConnectionsPercent":75,"MaxIdleConnectionsPercent":50}' \
  --region us-east-1

# Associate the target (Aurora cluster — NOT an individual instance)
aws rds create-db-proxy-target \
  --db-proxy-name "$PROXY_ID" --target-group-name "default" \
  --db-cluster-identifier "my-aurora-cluster" --region us-east-1
```

The proxy endpoint is available after creation — applications connect
to THIS endpoint, not the cluster endpoint.

## Step 2 — Secrets Manager integration

The proxy reads database credentials from Secrets Manager. The secret
must be in a specific JSON format.

```bash
# Verify the secret format
aws secretsmanager get-secret-value \
  --secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc" \
  --query 'SecretString' --output text --region us-east-1 | jq .
# Expected: { "username": "...", "password": "...", "engine": "postgres",
#   "host": "...", "port": 5432, "dbClusterIdentifier": "..." }
```

**IAM role policy (proxy must read the secret):**

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-*"
}
```

**Enable rotation (recommended):**

```bash
aws secretsmanager rotate-secret \
  --secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc" \
  --rotation-lambda-arn "arn:aws:lambda:us-east-1:123456789012:function:secretsmanager-rds-rotation" \
  --rotation-rules '{"AutomaticallyAfterDays":30}' --region us-east-1
```

When the secret rotates, the proxy picks up the new credentials without
dropping connections.

## Step 3 — IAM authentication

IAM auth allows applications to authenticate using IAM tokens instead of
passwords. This requires TLS.

```bash
aws rds create-db-proxy \
  --db-proxy-name "my-app-proxy-iam" \
  --engine-family POSTGRESQL \
  --auth '[{"AuthScheme":"SECRETS","SecretArn":"...","IAMAuth":"ENABLED"}]' \
  --role-arn "arn:aws:iam::123456789012:role/rds-proxy-role" \
  --vpc-subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --vpc-security-group-ids sg-proxy111 \
  --require-tls --region us-east-1
```

**IAM auth + TLS coupling:** IAM auth REQUIRES TLS (`--require-tls`).
The IAM token is generated by the AWS signer and is valid for 15 minutes.

**Application IAM policy for database access:**

```json
{
  "Effect": "Allow",
  "Action": "rds-db:connect",
  "Resource": "arn:aws:rds-db:us-east-1:123456789012:dbproxy:prx-abc123/*"
}
```

## Step 4 — TLS/SSL enforcement (require TLS)

TLS ensures encryption in transit between application and proxy, and
between proxy and database.

```bash
aws rds create-db-proxy --db-proxy-name "my-app-proxy" --require-tls ...
```

**When to require TLS:** ALWAYS for production. REQUIRED if using IAM
auth. Recommended for all environments.

## Step 5 — DB subnet group and multi-AZ

RDS Proxy requires a DB subnet group spanning at least 2 AZs for
multi-AZ deployment.

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name "my-proxy-subnet-group" \
  --db-subnet-group-description "Subnet group for RDS Proxy" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc --region us-east-1
```

Verify subnet AZ distribution:

```bash
aws ec2 describe-subnets --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone}' \
  --region us-east-1 --output table
```

If all subnets are in the same AZ, the proxy is single-AZ and not highly
available.

## Step 6 — Security group associations

The proxy has its own security group. The DATABASE security group must
allow ingress from the proxy security group on the database port.

```bash
# Create proxy SG
PROXY_SG=$(aws ec2 create-security-group --group-name "rds-proxy-sg" \
  --description "Security group for RDS Proxy" --vpc-id vpc-aaa11122 \
  --query 'GroupId' --output text --region us-east-1)

# CRITICAL: allow ingress from proxy SG to database SG
aws ec2 authorize-security-group-ingress \
  --group-id sg-database222 --protocol tcp --port 5432 \
  --source-security-group-id "$PROXY_SG" --region us-east-1
```

**The database SG → proxy SG ingress rule is the #1 forgotten network
configuration.** Without it, the proxy creates but connections time out.

## Step 7 — Max connections sizing (ACU-based)

Max connections are configured on the target group, NOT the proxy
itself.

```bash
aws rds modify-db-proxy-target-group \
  --db-proxy-name "my-app-proxy" --target-group-name "default" \
  --connection-pool-config '{
    "MaxConnectionsPercent": 75,
    "MaxIdleConnectionsPercent": 50,
    "ConnectionBorrowTimeout": 120,
    "SessionPinningFilters": ["EXCLUDE_VARIABLE_SETS"]
  }' --region us-east-1
```

| Parameter | Default | Recommendation |
|---|---|---|
| MaxConnectionsPercent | 90 | 75 for mixed workloads; 90 for proxy-only |
| MaxIdleConnectionsPercent | 50 | 50 (half of max for quick ramp-up) |
| ConnectionBorrowTimeout | 120 | 120s (increase if connection storms cause timeouts) |
| SessionPinningFilters | [] | `["EXCLUDE_VARIABLE_SETS"]` for PostgreSQL |

## Step 8 — CloudWatch metrics and monitoring

RDS Proxy emits CloudWatch metrics automatically. Key metrics:

| Metric | Description | Alert threshold |
|---|---|---|
| DatabaseConnections | Active connections via proxy | Trend approaching MaxConnectionsPercent |
| CPUUtilization | Proxy CPU usage | Sustained > 80% |
| MaxConnectionsPercent | Current connections as % of max | Sustained > 90% |

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-proxy-high-connections" \
  --namespace "AWS/RDS" --metric-name "DatabaseConnections" \
  --dimensions Name=DBProxy,Value=my-app-proxy \
  --statistic Average --period 300 --threshold 200 \
  --comparison-operator GreaterThanThreshold --evaluation-periods 2 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:alerts" --region us-east-1
```

## Step 9 — Failover handling

For Aurora clusters, RDS Proxy improves failover resilience. When the
cluster fails over (writer changes), the proxy redirects connections to
the new writer — typically within seconds.

```text
Aurora failover WITHOUT proxy:
  Writer A fails → app connections drop → Aurora promotes B →
  DNS update propagates (30-120s) → app reconnects
  Total downtime: 30-120 seconds

Aurora failover WITH proxy:
  Writer A fails → proxy detects → Aurora promotes B →
  proxy reroutes pooled connections → app connections PRESERVED
  Total perceived downtime: 0-5 seconds
```

## Step 10 — Aurora Serverless v2 compatibility

RDS Proxy supports Aurora Serverless v2. The proxy target should be the
CLUSTER (not an individual instance). The proxy automatically routes to
the writer and handles failover.

For Serverless v2, a lower MaxConnectionsPercent is recommended at
higher ACU levels because the cluster is already scaling.

| ACU Range | Approx max_connections | Recommended % |
|---|---|---|
| 2-4 (min) | ~90-180 | 75-90 |
| 4-16 | ~180-750 | 75 |
| 16-64 | ~750-3000 | 60-75 |

## NEVER do these things

1. **NEVER connect applications to the cluster endpoint when a proxy is
   deployed.** The proxy has its OWN endpoint. Using the cluster endpoint
   bypasses the proxy entirely.

2. **NEVER create a proxy without verifying the Secrets Manager secret
   format.** The secret must be JSON with `username`, `password`,
   `engine`, `host`, `port`, `dbClusterIdentifier`. Malformed secret =
   `Unavailable` status.

3. **NEVER set MaxConnectionsPercent at the proxy level.** It is set on
   the TARGET GROUP (`modify-db-proxy-target-group`), NOT on
   `create-db-proxy`.

4. **NEVER enable IAM authentication without TLS.** IAM auth REQUIRES
   `--require-tls`.

5. **NEVER forget the database SG → proxy SG ingress rule.** Without it,
   connections time out. This is the #1 network configuration issue.

6. **NEVER create a proxy with a single-AZ subnet group.** Multi-AZ
   requires subnets in at least 2 AZs.

7. **NEVER set MaxConnectionsPercent to 100.** Leave at least 10%
   headroom for admin/monitoring connections.

8. **NEVER assume the proxy enables Secrets Manager rotation
   automatically.** Rotation must be configured separately on the secret.

9. **NEVER use a proxy with unsupported database engines.** Proxy
   supports MySQL and PostgreSQL only (including Aurora variants).

10. **NEVER target an individual instance for Aurora clusters.** The
    target should be the CLUSTER (`--db-cluster-identifier`). Targeting
    an instance defeats the failover benefit.

## Output format

```text
RDS_PROXY: <proxy-name> (<proxy-endpoint>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Proxy name: <name>
  [✓|✗] Engine family: MYSQL | POSTGRESQL
  [✓|✗] Target: <aurora-cluster-name> (cluster) | <db-instance-id> (instance)
  [✓|✗] Secrets Manager secret: <secret-arn> (format verified)
  [✓|✗] IAM role: <role-arn> (trusts rds.amazonaws.com)
  [✓|✗] Secrets Manager rotation: enabled (<N> days) | disabled
  [✓|✗] IAM authentication: ENABLED (requires TLS) | DISABLED
  [✓|✗] TLS/SSL: required | not required
  [✓|✗] DB subnet group: <name> (subnets in <N> AZs)
  [✓|✗] Security group (proxy): <sg-id>
  [✓|✗] Security group (database → proxy ingress): ALLOWED on port <port>
  [✓|✗] Max connections percent: <percent>%
  [✓|✗] Max idle connections percent: <percent>%
  [✓|✗] Multi-AZ: YES (2+ AZs) | NO (single-AZ)
  [✓|✗] Proxy endpoint: <proxy-endpoint> (applications connect here)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws rds describe-db-proxies --db-proxy-name <name> --region <region>
  aws secretsmanager get-secret-value --secret-id <secret-arn> --region <region>
  aws rds describe-db-proxy-target-groups --db-proxy-name <name> --region <region>
```

### Worked example — Aurora PostgreSQL proxy with IAM auth and TLS

```text
RDS_PROXY: my-app-proxy (my-app-proxy.proxy-abc123.us-east-1.rds.amazonaws.com)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Proxy name: my-app-proxy
  [✓] Engine family: POSTGRESQL
  [✓] Target: my-aurora-cluster (cluster)
  [✓] Secrets Manager secret: arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/db-credentials-abc (format verified)
  [✓] IAM role: arn:aws:iam::123456789012:role/rds-proxy-role (trusts rds.amazonaws.com)
  [✓] Secrets Manager rotation: enabled (30 days)
  [✓] IAM authentication: ENABLED (requires TLS)
  [✓] TLS/SSL: required (--require-tls)
  [✓] DB subnet group: my-proxy-subnet-group (subnets in 3 AZs: us-east-1a, us-east-1b, us-east-1c)
  [✓] Security group (proxy): sg-proxy111
  [✓] Security group (database → proxy ingress): ALLOWED on port 5432
  [✓] Max connections percent: 75%
  [✓] Max idle connections percent: 50%
  [✓] Multi-AZ: YES (subnets span 3 AZs)
  [✓] Proxy endpoint: my-app-proxy.proxy-abc123.us-east-1.rds.amazonaws.com
  [✓] Tags: Environment=production, Application=my-app
VERIFICATION_COMMANDS:
  aws rds describe-db-proxies --db-proxy-name my-app-proxy --region us-east-1
  aws secretsmanager get-secret-value --secret-id rds/db-credentials-abc --region us-east-1
  aws rds describe-db-proxy-target-groups --db-proxy-name my-app-proxy --region us-east-1
```

## Error handling

### Proxy status is Unavailable
- Secret format is wrong or IAM role cannot read the secret. Verify JSON
  keys and role permissions.

### Connections time out
- Database SG does not allow ingress from proxy SG. Add the ingress rule
  on the database port.

### Application gets no connection pooling benefit
- Application is connecting to the cluster endpoint. Update the
  connection string to the proxy endpoint.

### IAM auth fails
- TLS not enforced. IAM auth REQUIRES `--require-tls`.

### Proxy connections exhausted during spikes
- MaxConnectionsPercent too low. Increase it, or scale up the Aurora
  instance class/ACU.

## Domain

AWS CloudOps / Amazon RDS Proxy Provisioning & Database Connection
Pooling.

## AWS documentation

- **RDS Proxy User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html
- **Managing RDS Proxy** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-managing.html
- **Secrets Manager integration** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-secrets.html
- **IAM authentication** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-iam-auth.html
- **Aurora Serverless v2** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html
- **Connection pooling tuning** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-connection-pool.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-metrics.html
