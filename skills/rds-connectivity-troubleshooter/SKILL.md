---
name: rds-connectivity-troubleshooter
description: Diagnoses RDS and Aurora connection failures through a bidirectional- SG-first decision tree covering security group misconfiguration (wrong SG attached, missing inbound on the RDS SG, missing egress on the client SG), subnet group errors, DNS resolution (custom vs cluster vs writer vs reader endpoint), IAM database auth failures (token expiry, policy scope), SSL/TLS issues (force_ssl, CA bundle rds-ca-2019/e2022, TLS version mismatch), max_connections reached (parameter group override, Aurora derived limit), storage-full status (auto-scaling not enabled), CPU/memory exhaustion, read replica lag, Aurora global database replication issues, RDS Proxy connectivity, parameter group and option group conflicts. Walks describe-db-instances + describe-security-groups to a verified root cause. Emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA. Use when an application cannot reach an RDS or Aurora database, intermittent connectivity, auth/TLS errors, pool exhaustion, or DNS lookup failures against an RDS endpoint.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and instance metadata. Live-account diagnosis uses aws rds describe-db-instances, describe-db-clusters, describe-events, describe-db-subnet-groups, describe-db-parameter-groups, describe-option-groups, aws ec2 describe-security-groups, describe-network-acls, describe-route-tables, describe-vpc-endpoints, aws logs get-log-events / filter-log-events...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing why an application cannot reach an RDS or Aurora database — connection timeout (SG, subnet, NACL, route table), authentication failure (master credentials, IAM database auth, expired password), SSL/TLS handshake error (force_ssl, CA bundle, TLS version), connection refused (instance unavailable, Multi-AZ failover, maintenance window, storage-full), too many connections (max_connections, Aurora derived limit, RDS Proxy), high latency (CPU/memory exhaustion, read replica lag), DNS resolution failure (custom endpoint, cluster endpoint, cross-region), or RDS Proxy connectivity issues.
  when_not_to_use: Query-level performance tuning (use Performance Insights + slow query log); RDS instance configuration posture audits (use rds-instance-auditor); Aurora failover automation (use aurora-failover-operator); RDS backup and restore operations (use rds-backup-restore-operator); parameter group authoring (use rds-parameter-group-deployer).
  activation_triggers: RDS connection timeout, cannot connect to RDS, Aurora connection failed, authentication failed for database, FATAL password authentication failed, Access denied for user, SSL connection required, TLS handshake failed RDS, connection refused RDS, too many connections RDS, FATAL too many connections, RDS storage-full, RDS CPU exhaustion, read replica lag, Aurora global database replication, RDS Proxy unreachable, parameter group max_connections override, option group conflict, RDS DNS not resolving
  invocation_schema: 'Input: either (a) a symptom description (the error string or observed behaviour, the DB instance or cluster identifier), OR (b) a live-account scenario where the agent runs aws rds describe-db-instances / describe-db-clusters / describe-events / describe-security-groups to gather evidence. Output: a deterministic TARGET / VERDICT / ROOT_CAUSE / REASON / EVIDENCE / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and ROOT_CAUSE names the specific failure category (NETWORK_SG_INBOUND / NETWORK_SG_EGRESS / NETWORK_NACL / NETWORK_ROUTE / NETWORK_SUBNET_GROUP / NETWORK_CROSS_VPC / DNS_CUSTOM_ENDPOINT / DNS_CLUSTER_ENDPOINT / AUTH_CREDENTIALS / AUTH_IAM_DB / AUTH_EXPIRED / TLS_CONFIG / TLS_CERT / INSTANCE_UNAVAILABLE / INSTANCE_FAILOVER / INSTANCE_MAINTENANCE / INSTANCE_STORAGE_FULL / CAPACITY_MAX_CONNECTIONS / CAPACITY_DERIVED_LIMIT / CAPACITY_PROXY / RESOURCE_CPU / RESOURCE_MEMORY / REPLICATION_LAG / GLOBAL_DB_REPLICATION / PARAM_GROUP_OVERRIDE / OPTION_GROUP_CONFLICT / UNKNOWN).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: RDS, Aurora, connection timeout, security group, bidirectional SG, subnet group, DB subnet group, DNS resolution, custom endpoint, cluster endpoint, writer endpoint, reader endpoint, IAM database auth, SSL, TLS, force_ssl, require_secure_transport, CA bundle, rds-ca-2019, rds-ca-e2022, max_connections, Aurora derived limit, storage-full, storage auto-scaling, CPU exhaustion, memory exhaustion, read replica lag, Aurora global database, RDS Proxy, parameter group, option group
  tags: rds, aurora, databases, troubleshoot, connectivity, security-group, tls, iam-db-auth, storage-full
---

# RDS Connectivity Troubleshooter

## Quick navigation

| Symptom / signal | Jump | Likely ROOT_CAUSE |
|---|---|---|
| `connection timed out` / `Could not connect to server` | Step 1 | `NETWORK_SG_INBOUND` (most common) or `NETWORK_SG_EGRESS` |
| `connection refused` (RST returned) | Step 2 | `INSTANCE_UNAVAILABLE` / `INSTANCE_FAILOVER` / `INSTANCE_MAINTENANCE` / `INSTANCE_STORAGE_FULL` |
| `FATAL: password authentication failed` / `Access denied for user` | Step 3 | `AUTH_CREDENTIALS` or `AUTH_IAM_DB` |
| `SSL connection required` / `TLS handshake failed` | Step 4 | `TLS_CONFIG` (`force_ssl` / `require_secure_transport`) or `TLS_CERT` |
| `FATAL: too many connections` / pool exhaustion | Step 5 | `CAPACITY_MAX_CONNECTIONS` / `CAPACITY_DERIVED_LIMIT` / `CAPACITY_PROXY` |
| `could not translate host name` / `nodename nor servname provided` | Step 6 | `DNS_CUSTOM_ENDPOINT` / `DNS_CLUSTER_ENDPOINT` |
| writer endpoint routes to a reader after failover | Step 6 | `DNS_CLUSTER_ENDPOINT` (Aurora writer DNS update lag) |
| `storage-full` status in describe-db-instances | Step 2 | `INSTANCE_STORAGE_FULL` (auto-scaling not enabled) |
| Aurora global database secondary lag > 1 minute | Step 7 | `GLOBAL_DB_REPLICATION` |
| read replica `ReplicaLag` > 30s and rising | Step 7 | `REPLICATION_LAG` |
| RDS Proxy `could not connect to proxy` | Step 8 | `CAPACITY_PROXY` (proxy SG / secrets) |
| parameter group change preceded the failure | Step 9 | `PARAM_GROUP_OVERRIDE` |
| option group change preceded the failure | Step 9 | `OPTION_GROUP_CONFLICT` |
| Symptom does not match any row, evidence incomplete | Step 10 | `INSUFFICIENT_DATA` |

## STRICT output contract

Every invocation MUST emit exactly one diagnostic block as the final
answer. The block is machine-parsable; any drift breaks the eval
harness and the downstream orchestrator.

```text
TARGET: <db-instance-identifier / cluster-identifier / endpoint>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <CATEGORY_NAME>
REASON: <1-3 sentences naming the failing config element + the probe
  that proves it>
EVIDENCE:
  - <observed signal — error string / instance status / metric>
  - <failing probe — CLI command and the specific output line that
    confirms the cause>
  - <passing probes — categories ruled out with one-line justification>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <resource>. Proceed? (yes/no)"
```

Rules:

- `VERDICT: ROOT_CAUSE_IDENTIFIED` requires at least one FAILING probe
  that matches the symptom — never a process-of-elimination answer.
- `VERDICT: INSUFFICIENT_DATA` MUST list the missing inputs and the
  next probe to run; it is never a dead-end.
- `ROOT_CAUSE` is a single UPPER_SNAKE_CASE category name from the set
  above — free-text root causes are forbidden.
- `EVIDENCE` lists BOTH the failing probe AND the categories ruled out.
- One block per target; multi-target incidents separate blocks with `---`.

## NEVER

- **NEVER** declare `ROOT_CAUSE_IDENTIFIED` without a failing probe
  that matches the symptom. A `connection timed out` alone is a
  symptom; the failing probe is the specific SG rule, NACL rule, or
  route that drops the packet.
- **NEVER** check only the RDS security group for a connection timeout.
  Security group rules are BIDIRECTIONAL — the client's SG must allow
  egress on the DB port AND the RDS SG must allow ingress from the
  client's SG (or CIDR). Operators who fix the RDS-side rule and skip
  the client-side egress rule see the timeout persist and conclude
  "security groups are fine." Always inspect BOTH SGs.
- **NEVER** assume the Aurora cluster endpoint points at the writer.
  The cluster endpoint follows the writer after a failover, but DNS
  caches (resolver, JVM, application) can serve a stale record for the
  TTL window (default 1s for the cluster endpoint, longer for cached
  resolvers). After a failover, the old writer becomes a reader and
  the cluster endpoint updates — but a write to a reader throws
  `ERROR: cannot execute INSERT in a read-only transaction`. Always
  confirm what the endpoint currently resolves to.
- **NEVER** treat `storage-full` as a capacity metric issue. When an
  RDS instance hits `storage-full`, it STOPS accepting writes — the
  application sees connection errors, query timeouts, or `disk full`
  errors. The instance status in `describe-db-instances` shows
  `StorageStatus: storage-full`. The fix is enabling storage
  auto-scaling (or allocating more storage); raising
  `max_connections` does nothing.
- **NEVER** confuse IAM database auth with the master credentials.
  IAM database auth generates a short-lived (15-minute) SigV4 token
  used as the password; the master credentials are static. A
  `password authentication failed` for an IAM-auth flow means the
  token expired OR the IAM policy lacks `rds-db:connect` OR the
  database user was not created with `AWSAuthenticationPlugin`. Adding
  `rds-db:connect` to a user connecting with the master password is a
  no-op.
- **NEVER** recommend disabling `force_ssl` / `require_secure_transport`
  to fix a TLS error in production. The TLS error is a SYMPTOM of a
  legitimate mismatch (wrong CA bundle, TLS 1.0 against a TLS 1.2+
  instance, missing `sslmode` in the connection string). Disabling
  encryption is a security regression.
- **NEVER** assume a read replica is queryable. A replica in
  `Replicating` state but with `ReplicaLag` climbing is falling behind
  — reads return stale data and CPU is saturated by replication
  replay. Always check `ReplicaLag` before routing reads to a replica.

## Expert heuristic

The three expert-heuristic deep dives (bidirectional SG check order, Aurora
writer/reader routing, storage-full) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph

The connectivity configuration dependency graph (ASCII) and its
read-top-down guidance moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Mindset

An RDS connection failure is almost never a database-engine problem.
The engine is fine; the broken thing is a security group rule, a
subnet group misconfiguration, an expired IAM token, a TLS mismatch, a
storage-full instance, or a stale DNS cache. Senior database engineers
start with `describe-db-instances` (for the instance status, endpoint,
SG list, and subnet group) and `describe-security-groups` (for both
the RDS SG and the client SG), then drill into engine logs only after
the network and auth layers are confirmed clean. Operators who start
with the slow query log miss a `storage-full` status that fired
BEFORE the query reached the engine.

## Process — bidirectional-SG-first diagnostic tree

### Step 0: Pre-flight — gather instance and client state

Instance/cluster/events/client-state gathering commands (probes 1-4) moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

Short-circuit cases that mimic connectivity failure:

| Signal | Effect on diagnosis |
|---|---|
| `DBInstanceStatus: deleted` / `deleting` | Instance is gone; emit `INSUFFICIENT_DATA` listing the deleted instance. |
| `DBInstanceStatus: modifying` | Instance is in a maintenance window; connections may drop briefly. Wait and re-check. |
| `DBInstanceStatus: incompatible-restore` / `incompatible-parameters` | Parameter group change broke the engine; fold to Step 9. |
| `StorageStatus: storage-full` | Instance stopped accepting writes; fold to Step 2 (`INSTANCE_STORAGE_FULL`). |
| AWS Health event `AWS_RDS_SERVICE` open in the region | Fold to AWS-side; surface the event ARN. Do NOT continue customer-side diagnosis. |

If the input lacks the instance identifier or the symptom, emit
`INSUFFICIENT_DATA` listing the missing fields.

### Step 1: Connection timeout — bidirectional security group

Symptom: `connection timed out`, `Could not connect to server`,
`TimeoutExpired`, or the TCP SYN goes unanswered. This is a packet
drop, NOT an auth or TLS issue.

#### 1a: RDS SG inbound (most common)

```bash
aws ec2 describe-security-groups --group-ids <rds-sg-id> --output json | \
  jq('.SecurityGroups[0].IpPermissions')
```

The RDS SG must have an inbound rule allowing the client's SG (or
CIDR) on the DB port (5432 for Postgres, 3306 for MySQL, 1433 for
SQL Server, 1521 for Oracle, 5439 for Redshift). If the rule is
missing or scoped to a different SG / CIDR, **ROOT_CAUSE_IDENTIFIED**
with `ROOT_CAUSE: NETWORK_SG_INBOUND`.

#### 1b: Client SG egress (the other half of the bidirectional check)

```bash
aws ec2 describe-security-groups --group-ids <client-sg-id> --output json | \
  jq('.SecurityGroups[0].IpPermissionsEgress')
```

The client SG must allow egress to the RDS endpoint on the DB port.
The default egress is allow-all (0.0.0.0/0); a locked-down SG with a
restricted egress (e.g., only 443) silently drops the DB-bound SYN. If
the egress rule is missing, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: NETWORK_SG_EGRESS`.

#### 1c: NACL and route table (deeper network)

If both SGs allow the flow, check the NACL on both subnets (NACLs are
stateless — both inbound and outbound rules must allow the flow in
both directions) and the route table (for cross-VPC peering / TGW
routes). Fold to `NETWORK_NACL` or `NETWORK_ROUTE`.

### Step 2: Connection refused — instance-level failure

Symptom: `connection refused` (RST returned, not a timeout). The
network path is open but the DB engine is not accepting connections.

| describe-db-instances signal | ROOT_CAUSE |
|---|---|
| `DBInstanceStatus: available` but `StorageStatus: storage-full` | `INSTANCE_STORAGE_FULL` — enable storage auto-scaling |
| `DBInstanceStatus: modifying` | `INSTANCE_MAINTENANCE` — wait for the window to complete |
| Recent event `DB instance restarted` / `Multi-AZ failover completed` | `INSTANCE_FAILOVER` — the writer changed; application DNS cache may be stale |
| `DBInstanceStatus: stopped` / `starting` | `INSTANCE_UNAVAILABLE` — start the instance |
| `DBInstanceStatus: incompatible-*` | Fold to Step 9 (parameter or option group) |

For `storage-full`: confirm with `describe-db-instances` showing
`StorageStatus: storage-full`. The fix is:

```bash
aws rds modify-db-instance --db-instance-identifier <id> \
  --storage-auto-scaling --max-allocated-storage <N> --apply-immediately
```

### Step 3: Authentication failure — credentials vs IAM DB auth

Symptom: `FATAL: password authentication failed for user "..."`,
`Access denied for user`, or `28000: authentication failed`.

#### 3a: Master / static credentials

If the connection uses a static password (Secrets Manager, hardcoded,
or env var), the credentials are wrong, rotated, or stale. Check
Secrets Manager:

```bash
aws secretsmanager get-secret-value --secret-id <secret-id> \
  --output json | jq('.SecretString')
```

Compare the username / password against what the application is using.
If the secret was rotated and the application cached the old value,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: AUTH_CREDENTIALS`.

#### 3b: IAM database auth

If `IAMDatabaseAuthenticationEnabled: true` and the application uses
an SigV4 token as the password, the token expires after 15 minutes.
Check:

1. The IAM policy attached to the application's role must include
   `rds-db:connect` on the DB instance ARN.
2. The database user must exist with
   `AWSAuthenticationPlugin: rds_iam` (Postgres) or
   `AWSAuthenticationPlugin: mysql_native_password` (MySQL).
3. The token must be regenerated before each connection (or at least
   every 14 minutes).

```bash
# Verify the IAM policy grants rds-db:connect
aws iam simulate-principal-policy \
  --policy-source-arn <app-role-arn> \
  --action-names rds-db:connect \
  --resource-arns arn:aws:rds-db:<region>:<account>:dbuser:<instance>/<user> \
  --output json
```

If `implicitDeny`, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: AUTH_IAM_DB`. If the token is older than 15 minutes,
`ROOT_CAUSE: AUTH_EXPIRED`.

### Step 4: SSL / TLS errors

Symptom: `SSL connection required`, `TLS handshake failed`,
`no SSL capabilities`, or `certificate verify failed`.

#### 4a: force_ssl / require_secure_transport

```bash
aws rds describe-db-instances --db-instance-identifier <id> \
  --output json | jq('.DBInstances[0] | .DBParameterGroups')
```

If the parameter group has `rds.force_ssl: 1` (Postgres) or
`require_secure_transport: 1` (MySQL) and the client connects without
`sslmode=require` (or the MySQL equivalent), the connection is
rejected. **ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: TLS_CONFIG`.

#### 4b: CA bundle mismatch

```bash
aws rds describe-db-instances --db-instance-identifier <id> \
  --output json | jq('.DBInstances[0].CACertificateIdentifier')
```

If the instance uses `rds-ca-e2022` (the recommended rotation) but the
client's trust store has `rds-ca-2019`, the TLS handshake fails with
`certificate verify failed`. **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: TLS_CERT`. Fix: update the client trust store with the
new CA bundle from the AWS RDS docs.

### Step 5: Too many connections — capacity

Symptom: `FATAL: too many connections`,
`FATAL: remaining connection slots are reserved for non-replication
superuser connections`, or connection pool exhaustion at the client.

#### 5a: max_connections (RDS for MySQL / Postgres)

```bash
aws rds describe-db-instances --db-instance-identifier <id> \
  --output json | jq('.DBInstances[0].DBParameterGroups')
```

If a parameter group overrides `max_connections` below the default,
**ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: CAPACITY_MAX_CONNECTIONS` (or
`PARAM_GROUP_OVERRIDE` if the override is the root issue).

#### 5b: Aurora derived limit

Aurora derives `max_connections` from the instance class
(`LEAST({DBInstanceClassMemory/9531392, 5000})` for Aurora
PostgreSQL). Upsizing the instance class raises the limit
automatically. If the application exceeds the derived limit,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: CAPACITY_DERIVED_LIMIT`.
Fix: upsize the instance class OR add an RDS Proxy to pool
connections.

#### 5c: RDS Proxy not absorbing the load

If an RDS Proxy is configured but the application still hits
`too many connections`, the proxy may be misconfigured (wrong target
SG, wrong secrets, or the application is bypassing the proxy
endpoint). Fold to Step 8.

### Step 6: DNS resolution — custom vs cluster endpoint

Symptom: `could not translate host name`, `nodename nor servname`,
or the application connects to the wrong instance after a failover.

#### 6a: Custom endpoint vs cluster endpoint

Aurora custom endpoints route to a subset of instances; the cluster
endpoint follows the writer; the reader endpoint round-robins across
readers. If the application uses a custom endpoint for writes but the
custom endpoint only includes readers, every write fails with
`cannot execute INSERT in a read-only transaction`.

```bash
aws rds describe-db-clusters --db-cluster-identifier <cluster> \
  --output json | jq('.DBClusters[0] | {
    CustomEndpoints: .CustomEndpoints,
    Endpoint, ReaderEndpoint,
    Members: [.DBClusterMembers[] | {DBInstanceIdentifier,
      IsClusterWriter}]}')
```

Confirm the endpoint includes the writer. **ROOT_CAUSE_IDENTIFIED**
with `ROOT_CAUSE: DNS_CUSTOM_ENDPOINT` or `DNS_CLUSTER_ENDPOINT`.

#### 6b: Stale DNS after failover

Stale-DNS-after-failover guidance moved verbatim to
[references/connectivity-layer-reference.md](references/connectivity-layer-reference.md).

### Step 7: Replication lag — read replica and global database

#### 7a: Read replica lag

```bash
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=<replica-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

`ReplicaLag` > 30s and rising indicates the replica cannot keep up
with the source. Reads return stale data. **ROOT_CAUSE_IDENTIFIED**
with `ROOT_CAUSE: REPLICATION_LAG`. Fix: upsize the replica, reduce
write load on the source, or route reads elsewhere.

#### 7b: Aurora global database replication

For Aurora global databases, the secondary cluster replicates from
the primary over a dedicated channel. If the channel is interrupted
(network, AWS-side issue) or the secondary cannot keep up,
`ReplicationLag` on the secondary climbs. Check the secondary cluster
status and the AWS Health dashboard for cross-region issues.
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: GLOBAL_DB_REPLICATION`.

### Step 8: RDS Proxy connectivity

RDS Proxy probe commands and the common proxy failure pattern table moved verbatim to
[references/engine-auth-reference.md](references/engine-auth-reference.md).

### Step 9: Parameter group and option group misconfiguration

#### 9a: Parameter group override

The parameter-override culprit table moved verbatim to
[references/engine-auth-reference.md](references/engine-auth-reference.md).

#### 9b: Option group conflict

Option-group conflict patterns moved verbatim to
[references/engine-auth-reference.md](references/engine-auth-reference.md).

### Step 10: INSUFFICIENT_DATA — when to bail

Emit `INSUFFICIENT_DATA` when:

- The input lacks the instance identifier or endpoint and the symptom
  is too generic.
- A probe requires operator input (e.g., the application's connection
  string is unknown).
- The symptom matches no row in the quick navigation table and the
  describe-db-instances output is empty or stale.
- An AWS Health event is OPEN and may be the cause.

ALWAYS list the missing inputs and the exact next probe to run.

## Output format

See the STRICT output contract above. Two worked examples follow.

### Worked example — connection timeout, RDS SG missing inbound

```text
TARGET: db-prod-postgres (endpoint: db-prod-postgres.abc123.us-east-1.rds.amazonaws.com:5432)
VERDICT: ROOT_CAUSE_IDENTIFIED
ROOT_CAUSE: NETWORK_SG_INBOUND
REASON: The RDS SG (sg-rds-aaa) has no inbound rule allowing the
  application's SG (sg-app-bbb) on port 5432. The only inbound rule
  permits sg-old-ccc (a decommissioned SG). The client SG egress is
  allow-all (0.0.0.0/0), so the packet reaches the RDS subnet but is
  dropped at the RDS SG.
EVIDENCE:
  - Probe: aws ec2 describe-security-groups --group-ids sg-rds-aaa
    returns IpPermissions with one rule: port 5432 from sg-old-ccc —
    sg-app-bbb is absent.
  - Probe: aws ec2 describe-security-groups --group-ids sg-app-bbb
    returns IpPermissionsEgress: 0.0.0.0/0 all ports (egress is open).
  - Passing: describe-db-instances shows DBInstanceStatus: available,
    StorageStatus: healthy (instance is not the issue); the client is
    in the same VPC (route table is not the issue).
REMEDIATION:
  1. Add an inbound rule to sg-rds-aaa allowing sg-app-bbb on 5432:
     aws ec2 authorize-security-group-ingress --group-id sg-rds-aaa \
       --protocol tcp --port 5432 --source-security-group-id sg-app-bbb
  2. Verify from the client host: psql -h <endpoint> -U <user> -d <db>
     (should connect within seconds).
CONFIRM: Before adding the rule, emit and await:
  "CONFIRM: About to add inbound 5432 from sg-app-bbb to sg-rds-aaa.
   Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

The INSUFFICIENT_DATA worked example moved verbatim to
[references/worked-examples.md](references/worked-examples.md).

## Pre-flight safety checks

Pre-flight safety checks (confirm gate, read-only-first, disruption notes,
batch limit) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

## Remediation guidance

| ROOT_CAUSE | Specific fix |
|---|---|
| `NETWORK_SG_INBOUND` | Add inbound rule to the RDS SG for the client SG / CIDR on the DB port. |
| `NETWORK_SG_EGRESS` | Add egress rule to the client SG for the RDS endpoint on the DB port. |
| `NETWORK_NACL` / `NETWORK_ROUTE` | Add NACL / route table rule for bidirectional flow. |
| `NETWORK_SUBNET_GROUP` | Add a subnet in the client's AZ to the DB subnet group. |
| `INSTANCE_STORAGE_FULL` | Enable storage auto-scaling: `modify-db-instance --storage-auto-scaling --max-allocated-storage <N>`. |
| `INSTANCE_FAILOVER` | Wait for the cluster endpoint DNS to update; flush the app DNS cache. |
| `AUTH_CREDENTIALS` | Rotate / update the secret in Secrets Manager; refresh the app's cached value. |
| `AUTH_IAM_DB` | Add `rds-db:connect` to the app role; create the DB user with `AWSAuthenticationPlugin`. |
| `TLS_CONFIG` | Add `sslmode=require` (Postgres) or `requireSSL=true` (MySQL) to the connection string. |
| `TLS_CERT` | Update the client trust store with the CA bundle matching `CACertificateIdentifier`. |
| `CAPACITY_MAX_CONNECTIONS` / `CAPACITY_DERIVED_LIMIT` | Upsize the instance class OR add an RDS Proxy to pool connections. |
| `CAPACITY_PROXY` | Fix the proxy SG, secrets, or application connection string. |
| `REPLICATION_LAG` | Upsize the replica, reduce source write load, or route reads elsewhere. |
| `GLOBAL_DB_REPLICATION` | Check the secondary cluster status and AWS Health; recover or re-establish the channel. |
| `DNS_CUSTOM_ENDPOINT` / `DNS_CLUSTER_ENDPOINT` | Add the writer to the custom endpoint; flush DNS; use the writer endpoint for writes. |
| `PARAM_GROUP_OVERRIDE` | Revert or correct the parameter; reboot if required. |
| `OPTION_GROUP_CONFLICT` | Resolve the option conflict; re-apply the option group. |

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — expert-heuristic deep dives (bidirectional SG check order, Aurora writer/reader routing, storage-full) and the configuration dependency graph (moved from this file)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 0 pre-flight gathering commands (probes 1-4) and the pre-flight safety checks (moved from this file)
- [references/worked-examples.md](references/worked-examples.md) — the INSUFFICIENT_DATA worked example; the primary connection-timeout example stays in this file
- [references/engine-auth-reference.md](references/engine-auth-reference.md) — IAM DB auth, TLS/CA rotation, parameter and option group, storage-full, proxy, DNS detail; extended with Step 8 proxy probes, the 9a parameter-override table, and 9b option-group conflicts
- [references/connectivity-layer-reference.md](references/connectivity-layer-reference.md) — engine port registry, SG/NACL evaluation rules, Aurora endpoint behaviour, cross-VPC matrix, AWS Health event categories; extended with the 6b stale-DNS-after-failover guidance

## Domain

AWS CloudOps / RDS & Aurora Databases, Connectivity Diagnostics, VPC
Networking for Databases, IAM Database Authentication, TLS / SSL,
Storage Auto-Scaling, and Read Replica / Global Database Replication.

## AWS documentation

- RDS troubleshooting — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Troubleshooting.html
- Security group rules — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html
- IAM database auth — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html
- SSL/TLS — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html
- Storage auto-scaling — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIOPS.StorageTypes.html#USER_PIOPS.Autoscaling
- Aurora endpoints — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html
- Aurora global databases — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html
- RDS Proxy — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html
- Aurora failover — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html
