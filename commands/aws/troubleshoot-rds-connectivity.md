---
name: troubleshoot-rds-connectivity
description: >-
  Slash command for the rds-connectivity-troubleshooter skill. Diagnoses
  RDS or Aurora connection failures through a bidirectional-SG-first
  decision tree (SG inbound + egress, subnet group, DNS, IAM DB auth,
  TLS cert, max_connections, storage-full, replica lag, global DB, RDS
  Proxy, parameter / option group conflicts). Emits
  ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
skill: rds-connectivity-troubleshooter
family: Databases
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA"
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
  - "RDS storage-full"
  - "RDS high latency"
  - "read replica lag"
  - "RDS DNS not resolving"
  - "database endpoint unreachable"
  - "security group blocking RDS"
  - "troubleshoot RDS connectivity"
  - "diagnose database connection failure"
  - "RDS unreachable from application"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-rds-connectivity

Activate the `rds-connectivity-troubleshooter` skill and diagnose an RDS
or Aurora connection failure through the bidirectional-SG-first
diagnostic tree.

## What it does

Reads a symptom description (error message, observed behaviour, caller
context) plus the DB instance or cluster metadata, then walks the
diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — instance state (`describe-db-instances`), recent
   events (`describe-events`), AWS Health (regional incidents).
   Short-circuits on `deleting`, `failed`, `incompatible-*`,
   `storage-full`, or AWS-side failover events.
2. **Symptom entry** — map the error to one of: connection timeout,
   connection refused, auth failed, TLS error, too many connections,
   DNS resolution failure, replication lag, RDS Proxy unreachable.
3. **Layer-specific probes** — for timeouts, walk the bidirectional SG
   order: RDS SG inbound → client SG egress → NACL both directions →
   route table → DB subnet group → cross-VPC peering/TGW → final
   `nc -vz`. For auth: Secrets Manager value vs application string →
   IAM auth token expiry + policy scope → password expiry. For TLS:
   `rds.force_ssl` / `require_secure_transport` → CA bundle match →
   TLS version match. For storage-full: enable storage auto-scaling.
   For capacity: derived cap (Aurora) vs parameter cap (RDS) → RDS
   Proxy / pool tuning.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with a failing probe that
   matches the symptom) or INSUFFICIENT_DATA (list the missing inputs
   and the next probe).

Emits a deterministic diagnostic block per target:

```text
TARGET: <db-instance-identifier or endpoint>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <NETWORK_SG_INBOUND | NETWORK_SG_EGRESS | NETWORK_NACL |
  NETWORK_ROUTE | NETWORK_SUBNET_GROUP | NETWORK_CROSS_VPC |
  DNS_CUSTOM_ENDPOINT | DNS_CLUSTER_ENDPOINT | AUTH_CREDENTIALS |
  AUTH_IAM_DB | AUTH_EXPIRED | TLS_CONFIG | TLS_CERT |
  INSTANCE_UNAVAILABLE | INSTANCE_FAILOVER | INSTANCE_MAINTENANCE |
  INSTANCE_STORAGE_FULL | CAPACITY_MAX_CONNECTIONS |
  CAPACITY_DERIVED_LIMIT | CAPACITY_PROXY | RESOURCE_CPU |
  RESOURCE_MEMORY | REPLICATION_LAG | GLOBAL_DB_REPLICATION |
  PARAM_GROUP_OVERRIDE | OPTION_GROUP_CONFLICT | UNKNOWN>
REASON: <1-3 sentences naming the failing config element + the probe
  that proves it>
EVIDENCE:
  - <observed signal — error string / instance status / metric>
  - <failing probe — CLI command and the specific output line>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before any state-changing CLI, emit and await operator
  approval.
```

## When to invoke

Paste a symptom description and ask any of:

- "application cannot reach RDS — connection times out"
- "FATAL: password authentication failed"
- "SSL connection required after maintenance window"
- "connection refused from Aurora writer"
- "FATAL: too many connections"
- "RDS storage-full — writes failing"
- "RDS latency spike — queries timing out"
- "RDS endpoint not resolving from on-prem"
- "troubleshoot database connectivity"

## Inputs

- Symptom description: error string, observed behaviour, intermittent
  vs persistent pattern.
- DB instance or cluster metadata: identifier, engine, status,
  endpoint, security groups, subnet group, IAM auth flag, CA
  identifier, recent events.
- For live-account diagnosis: caller context — source EC2 / container,
  subnet, security group, region, AZ. The skill uses
  `describe-db-instances`, `describe-db-clusters`,
  `describe-security-groups`, `describe-network-acls`,
  `describe-route-tables`, `describe-db-subnet-groups`,
  `describe-events`, `describe-db-proxies`.

## Outputs

- One diagnostic block per target instance / cluster.
- ROOT_CAUSE value from the enumerated set above.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: SG rule additions, storage auto-scaling,
  credential rotation, CA bundle update, instance-class upsize, RDS
  Proxy recommendation, DNS flush, or parameter-group revert.

## References

- Skill: `skills/rds-connectivity-troubleshooter/SKILL.md`
- Reference: `skills/rds-connectivity-troubleshooter/references/connectivity-layer-reference.md`
- Reference: `skills/rds-connectivity-troubleshooter/references/engine-auth-reference.md`
- AWS docs: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Troubleshooting.html

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for RDS/Aurora connectivity).
- `/aws:audit-rds-instance` for configuration posture audits on the
  same instance (security exposure, encryption, deletion protection).
- `/aws:audit-ec2-security-groups` for security-group exposure audits
  on the caller side.
