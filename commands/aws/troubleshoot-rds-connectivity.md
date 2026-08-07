---
description: Diagnose RDS or Aurora connection failures through a seven-layer (timeout, auth, TLS, refused, capacity, latency, DNS) diagnostic tree — emits ROOT_CAUSE_FOUND with the specific connectivity layer or ESCALATE.
nl_triggers:
  - "RDS connection timeout"
  - "cannot connect to RDS"
  - "Aurora connection failed"
  - "authentication failed for database"
  - "FATAL password authentication failed"
  - "Access denied for user"
  - "SSL connection required"
  - "TLS handshake failed RDS"
  - "connection refused RDS"
  - "too many connections RDS"
  - "FATAL too many connections"
  - "MySQL server has gone away"
  - "RDS high latency"
  - "read replica lag"
  - "RDS DNS not resolving"
  - "database endpoint unreachable"
  - "security group blocking RDS"
  - "troubleshoot RDS connectivity"
  - "diagnose database connection failure"
  - "RDS unreachable from application"
routes_to: rds-connectivity-troubleshooter
---

# /aws:troubleshoot-rds-connectivity

Activate the `rds-connectivity-troubleshooter` skill and diagnose an RDS
or Aurora connection failure through the seven-layer diagnostic tree.

## What it does

Reads a symptom description (error message, observed behaviour, caller
context) plus the DB instance or cluster metadata, then walks the OSI-
aligned diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — instance state (`describe-db-instances`),
   recent events (`describe-events`), AWS Health (regional incidents).
   Short-circuits on `deleting`, `failed`, `incompatible-*`,
   `inaccessible-encrypt-credentials`, or AWS-side failover events.
2. **Symptom entry** — map the error to one of: timeout, auth failed,
   TLS error, connection refused, too many connections, latency, DNS.
3. **Layer-specific probes** — for timeouts, walk OSI order:
   - Source-IP reachability → SG inbound (RDS) → SG egress (caller) →
     NACL both directions both subnets → route table both subnets →
     subnet group → cross-VPC peering/TGW → final `nc -vz`.
   - For auth: Secrets Manager value vs application string → IAM auth
     enabled and policy scoped → password expiry → pg_hba / TLS
     requirement masquerading as auth error.
   - For TLS: `rds.force_ssl` / `require_secure_transport` → CA bundle
     match (rds-ca-2019/e2022/e2024) → TLS version match.
   - For refused: events for failover / maintenance / storage-full →
     port match.
   - For too-many-connections: derived cap (Aurora) vs parameter cap
     (RDS) → RDS Proxy / pool tuning.
   - For latency: CloudWatch CPUUtilization / ReplicaLag → Performance
     Insights top SQL → storage type (gp2 burst depletion).
   - For DNS: dig/nslookup from caller → Route 53 CNAME target →
     cross-region DNS resolution.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing probe that matches the
   symptom), NEED_MORE_INFO (a probe requires operator input), or
   ESCALATE (AWS-side incident; surface AWS Health event ARN).

Emits a deterministic diagnostic block per target:

```text
TARGET: <db-instance-identifier or endpoint>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <NETWORK_SG | NETWORK_NACL | NETWORK_ROUTE | NETWORK_SUBNET |
        NETWORK_CROSS_VPC | AUTH_CREDENTIALS | AUTH_IAM | AUTH_EXPIRED |
        TLS_CONFIG | TLS_CERT | INSTANCE_UNAVAILABLE | INSTANCE_FAILOVER |
        INSTANCE_MAINTENANCE | INSTANCE_STORAGE_FULL |
        CAPACITY_MAX_CONNECTIONS | CAPACITY_PROXY |
        LATENCY_INSTANCE_CLASS | LATENCY_STORAGE | LATENCY_REPLICA_LAG |
        DNS | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "application cannot reach RDS — connection times out"
- "FATAL: password authentication failed"
- "SSL connection required after maintenance window"
- "connection refused from Aurora writer"
- "FATAL: too many connections"
- "RDS latency spike — queries timing out"
- "RDS endpoint not resolving from on-prem"
- "troubleshoot database connectivity"

A bare endpoint + any connectivity verb ("cannot reach RDS",
"connection failure to Aurora", "db unreachable") also routes here via
the orchestrator.

## Inputs

- Symptom description: error string, observed behaviour, intermittent
  vs persistent pattern.
- DB instance or cluster metadata: identifier, engine, status,
  endpoint, security groups, subnet group, IAM auth flag, CA identifier,
  recent events.
- For live-account diagnosis: caller context — source EC2 instance or
  container, subnet, security group, region, AZ. The skill uses
  `describe-db-instances`, `describe-security-groups`,
  `describe-network-acls`, `describe-route-tables`,
  `describe-db-subnet-groups`, `describe-events`,
  `describe-db-engine-versions`.

## Outputs

- One diagnostic block per target instance/cluster.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: SG/NACL rule additions, route table update,
  credential rotation, CA bundle update, instance-class upsize, RDS
  Proxy recommendation, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for RDS/Aurora connectivity).
- `/aws:audit-rds-instance` for configuration posture audits on the
  same instance (security exposure, encryption, deletion protection).
- `/aws:audit-ec2-security-groups` for security-group exposure audits
  on the caller side.
