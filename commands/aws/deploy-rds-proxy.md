---
description: Provision an Amazon RDS Proxy with production-grade defaults (connection pooling, Secrets Manager integration, IAM authentication, TLS/SSL, multi-AZ subnet group, security groups, ACU-based max connections sizing, failover handling). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create rds proxy"
  - "deploy rds proxy"
  - "rds proxy connection pooling"
  - "rds proxy secrets manager"
  - "rds proxy iam authentication"
  - "rds proxy tls"
  - "aurora serverless v2 proxy"
  - "rds proxy multi-az"
  - "rds proxy max connections"
  - "rds proxy failover"
  - "rds proxy security group"
  - "rds proxy subnet group"
routes_to: rds-proxy-deployer
---

# /aws:deploy-rds-proxy

Activate the `rds-proxy-deployer` skill and provision an Amazon RDS
Proxy with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Connection pooling and target config (proxy endpoint vs cluster endpoint)
2. Secrets Manager integration (secret format, IAM role, rotation pairing)
3. IAM authentication (token-based auth, requires TLS)
4. TLS/SSL enforcement (require TLS)
5. DB subnet group and multi-AZ (2+ AZs required)
6. Security group associations (proxy SG, database SG ingress)
7. Max connections sizing (ACU-based percentage on target group)
8. CloudWatch metrics and monitoring (DatabaseConnections, CPUUtilization)
9. Failover handling (proxy reroutes on Aurora writer failover)
10. Aurora Serverless v2 compatibility (cluster target, dynamic ACU)
11. Recent features (Serverless v2 support, session pinning filters)

## When to use

- You need to create an RDS Proxy for connection pooling.
- You need to configure Secrets Manager integration for credentials.
- You need to enable IAM authentication for database access.
- You need to enforce TLS/SSL for the proxy.
- You need to size max connections based on Aurora ACU.
- You need multi-AZ proxy deployment.
- You need failover handling for Aurora clusters.
- You need to connect the proxy to Aurora Serverless v2.

## When NOT to use

- **Auditing existing proxies** — use RDS Proxy audit skills.
- **RDS instance creation itself** — use RDS deploy skills.
- **Aurora Global Database** — different connectivity model.

## How to invoke

### Slash command

```
/aws:deploy-rds-proxy
```

Then provide: proxy name, target (Aurora cluster or RDS instance),
engine family, Secrets Manager secret ARN, IAM role ARN, VPC subnet IDs
(2+ AZs), security group IDs, auth mode (IAM or password), TLS
requirement, max connections percent, tags.

### Natural language

Any of these routes to the same skill:

- "create an rds proxy for my aurora cluster"
- "set up connection pooling with rds proxy"
- "configure iam authentication for rds proxy"
- "deploy a multi-az rds proxy with failover"
- "size max connections for aurora serverless v2 proxy"

### CLI routing

```bash
node cli/bin/cli.js route "create an rds proxy"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or
configure RDS Proxy connections. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-rds-proxy

     Create an RDS Proxy for Aurora PostgreSQL cluster
     my-aurora-cluster with IAM auth, TLS required,
     Secrets Manager rotation, and multi-AZ across
     us-east-1a, 1b, 1c.

Skill:
  RDS_PROXY: my-app-proxy
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] IAM authentication: ENABLED (requires TLS)
    [✓] TLS/SSL: required
    [✓] Secrets Manager rotation: enabled (30 days)
    [✓] Multi-AZ: YES (3 AZs)
    [✓] Proxy endpoint: my-app-proxy.proxy-abc123.us-east-1.rds.amazonaws.com
  VERIFICATION_COMMANDS:
    aws rds describe-db-proxies --db-proxy-name my-app-proxy --region us-east-1
```

## References

- Skill definition: `skills/rds-proxy-deployer/SKILL.md`
- Secrets and IAM auth guide: `skills/rds-proxy-deployer/references/secrets-and-iam-auth.md`
- Subnet and sizing guide: `skills/rds-proxy-deployer/references/subnet-and-sizing.md`
- Eval suite: `skills/rds-proxy-deployer/evals/evals.json`
