---
name: rds-connectivity-troubleshooter
description: >-
  Diagnoses RDS and Aurora connection failures through a systematic seven-layer
  diagnostic tree — connection timeout (security group, subnet, route table,
  NACL, NAT, VPC peering/TGW), authentication failure (master credentials,
  IAM database auth, expired passwords, pg_hba.conf), SSL/TLS handshake errors
  (force_ssl, CA bundle rds-ca-2019/e2022, TLS version mismatch), connection
  refused (instance unavailable, Multi-AZ failover, maintenance window, wrong
  port), too many connections (max_connections, Aurora derived limit, RDS
  Proxy, Aurora Serverless scaling), high latency (instance class, storage
  type, read replica lag, Performance Insights), and DNS resolution failure
  (Route 53 CNAME, custom DNS, cross-region endpoint). Walks symptoms to root
  cause with verify-and-fix commands, emits ROOT_CAUSE_FOUND with the specific
  connectivity layer, NEED_MORE_INFO when a check requires operator input, or
  ESCALATE for AWS-side incidents. Use when application cannot reach an RDS
  or Aurora database, intermittent connectivity, auth errors, TLS errors,
  connection pool exhaustion, unexplained query latency, or DNS lookup
  failures against an RDS endpoint.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline symptom classification works from pasted error messages
  and instance metadata. Live-account diagnosis uses aws rds
  describe-db-instances, aws ec2 describe-security-groups, aws rds
  describe-db-subnet-groups, aws ec2 describe-route-tables, aws rds
  describe-events, aws rds describe-db-engine-versions, aws ec2
  describe-network-acls, and aws ec2 describe-vpc-peering-connections (AWS
  CLI v2, SSO or key-based credentials).
keywords:
  - RDS
  - Aurora
  - connectivity
  - connection timeout
  - authentication failed
  - SSL/TLS
  - certificate
  - rds.force_ssl
  - rds-ca-2019
  - rds-ca-e2022
  - connection refused
  - too many connections
  - max_connections
  - RDS Proxy
  - Aurora Serverless
  - high latency
  - read replica lag
  - Performance Insights
  - DNS resolution
  - Route 53 CNAME
  - security group
  - NACL
  - route table
  - subnet group
  - VPC peering
  - Transit Gateway
  - IAM database auth
  - pg_hba.conf
  - troubleshooting
tags: [rds, aurora, databases, networking, troubleshooting, connectivity, dns, tls, security-groups]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: troubleshoot
  skill_class: capability
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing an RDS or Aurora connection failure (timeout, auth error, TLS
    error, connection refused, pool exhaustion, latency, DNS), walking a
    symptom to the failed connectivity layer with verify and fix commands,
    validating an application's inability to reach its database, or
    triaging a "the database is down" page where the root cause may be
    network, auth, TLS, capacity, or DNS — not necessarily the database
    engine itself.
  when_not_to_use: >-
    Instance configuration posture audits (use rds-instance-auditor), query
    performance tuning or slow-query analysis (use Performance Insights
    directly), IAM policy authoring for rds-db:connect (use
    iam-least-privilege-advisor), KMS key access for encrypted instances
    (use kms-key-policy-auditor), or certificate-expiry monitoring for ACM
    (use acm-certificate-expiry-auditor). This skill diagnoses connectivity
    reachability and handshake; it does not audit configuration posture.
  activation_triggers:
    - "RDS connection timeout"
    - "cannot connect to RDS"
    - "Aurora connection failed"
    - "authentication failed for database"
    - "FATAL: password authentication failed"
    - "Access denied for user"
    - "SSL connection required"
    - "TLS handshake failed RDS"
    - "connection refused RDS"
    - "too many connections RDS"
    - "FATAL: too many connections"
    - "MySQL server has gone away"
    - "RDS high latency"
    - "read replica lag"
    - "RDS DNS not resolving"
    - "database endpoint unreachable"
    - "security group blocking RDS"
    - "troubleshoot RDS connectivity"
  invocation_schema: >-
    Input: either (a) a symptom description (error message, "application
    cannot reach the database," intermittent connection pattern), optionally
    paired with the DB instance metadata (describe-db-instances output),
    OR (b) a db-instance-identifier plus caller context (source subnet/SG,
    application region, observed error) for live-account diagnosis. Output:
    a deterministic ROOT_CAUSE/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION
    block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and
    LAYER ∈ {NETWORK_SG, NETWORK_NACL, NETWORK_ROUTE, NETWORK_SUBNET,
    NETWORK_CROSS_VPC, AUTH_CREDENTIALS, AUTH_IAM, AUTH_EXPIRED, TLS_CONFIG,
    TLS_CERT, INSTANCE_UNAVAILABLE, INSTANCE_FAILOVER, INSTANCE_MAINTENANCE,
    INSTANCE_STORAGE_FULL, CAPACITY_MAX_CONNECTIONS, CAPACITY_PROXY,
    LATENCY_INSTANCE_CLASS, LATENCY_STORAGE, LATENCY_REPLICA_LAG, DNS,
    UNKNOWN}.
  invocation_example: |-
    # Minimal valid input (offline symptom classification):
    Symptom: "application in us-east-1a cannot reach db-prod-mysql;
    connection times out after 10 seconds; no error in MySQL error log."
    DBInstanceIdentifier: db-prod-mysql
    Engine: mysql
    Endpoint: db-prod-mysql.cid.on.aws
    Port: 3306
    SecurityGroups: [{VpcSecurityGroupId: sg-aaa, Status: active}]
    DBSubnetGroup: prod-db-subnet-group
    Caller context: app-server in subnet subnet-bbb, security group sg-app,
    AZ us-east-1a
---

# RDS Connectivity Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  timeout → NETWORK_SG/NETWORK_NACL/NETWORK_ROUTE/NETWORK_SUBNET/NETWORK_CROSS_VPC;
  auth failed → AUTH_CREDENTIALS/AUTH_IAM/AUTH_EXPIRED; TLS/SSL error →
  TLS_CONFIG/TLS_CERT; connection refused → INSTANCE_UNAVAILABLE/
  INSTANCE_FAILOVER/INSTANCE_MAINTENANCE; too many connections →
  CAPACITY_MAX_CONNECTIONS/CAPACITY_PROXY; slow but connects →
  LATENCY_INSTANCE_CLASS/LATENCY_STORAGE/LATENCY_REPLICA_LAG; cannot resolve
  hostname → DNS.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_FOUND verdict requires
  positive evidence — a failing probe that matches the symptom — not a
  process of elimination that "must be the SG."
- **OSI ordering is non-negotiable for timeout symptoms.** DNS (L7) →
  routing (L3) → security group (L3-L4 stateful) → NACL (L4 stateless) →
  subnet/AZ (L2) → port reachability (L4) → TLS handshake (L5-L6) → auth
  (L7 application). Skipping layers produces false root causes.
- **ESCALATE for AWS-side incidents.** Multi-AZ failover in progress,
  storage-full, incompatible-parameters after engine upgrade, and AWS
  regional events are not customer-fixable — escalate to AWS Support and
  surface the event ARN.

## Mindset

A "database is down" page is usually a networking or auth incident wearing
a database costume. The engine is fine in the majority of cases; the
broken thing is reachability, identity, trust (TLS), or capacity. Treat the
database engine as innocent until the network, identity, and TLS layers
are proven clean. Senior database engineers do not start with the engine
logs; they start with the OSI stack and only open the engine error log
once L4 reachability is confirmed.

## Philosophy

Four behaviours separate a senior database-connectivity engineer from a
generalist:

- **Symptoms, not components, drive the diagnostic order.** A "connection
  timeout" tells you the SYN packet did not round-trip; that constrains
  the cause to L3-L4 (routing, SG, NACL, subnet/AZ, cross-VPC reachability).
  A "connection refused" tells you the SYN reached a port with no listener
  — that is an instance-state problem (down, failover, wrong port), not a
  network problem. A "TLS handshake error" tells you the TCP connection
  succeeded; do NOT re-check security groups. Routing the symptom to the
  wrong layer is the #1 source of wasted cycles in connectivity incidents.
- **Security groups are stateful; NACLs are stateless.** A SG inbound allow
  on 3306 implicitly allows the return traffic. A NACL inbound allow on
  3306 ALSO requires an outbound allow on the ephemeral port range
  (1024-65535) for the return packet, because NACLs are stateless. Operators
  who "fixed" the SG and still cannot connect often have a NACL denying the
  return path. Always check both directions on the NACL.
- **Aurora connection strings are DNS-driven and TTL-sensitive.** The
  cluster writer endpoint flips to the new writer on failover; reader
  endpoints rebalance across replicas. Clients that cache DNS for more than
  30 seconds (the JVM default `networkaddress.cache.ttl=60`) pin to the old
  IP after failover and fail with "connection refused" even though the
  cluster is healthy. Many "Aurora is down" incidents are actually "client
  DNS cache is stale" incidents. Always test from a fresh process before
  declaring the cluster unreachable.
- **IAM database auth is bounded and token-cached.** IAM auth generates an
  SigV4-signed token that is valid for 15 minutes. Application connection
  pools that hold IAM-auth connections longer than 15 minutes hit "auth
  failed" mid-traffic even though the SG, NACL, and TLS layers are clean.
  The fix is short connection lifetime or a switch to RDS Proxy (which
  handles credential refresh). Operators who debug this as "the password
  changed" waste hours on the wrong layer.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `Connection timed out`, `Operation timed out`, SYN no SYN-ACK | NETWORK_SG / NETWORK_NACL / NETWORK_ROUTE / NETWORK_SUBNET / NETWORK_CROSS_VPC | `aws ec2 describe-security-groups` + `aws ec2 describe-network-acls` for caller's subnet |
| `FATAL: password authentication failed`, `Access denied for user` | AUTH_CREDENTIALS | `aws secretsmanager get-secret-value` for the master secret |
| `FATAL: IAM authentication failed`, `Token is expired` | AUTH_IAM | `aws rds describe-db-instances` (IAMDatabaseAuthenticationEnabled) + IAM policy check |
| `password expired`, `account is locked` | AUTH_EXPIRED | Engine-specific (`ALTER USER ... PASSWORD EXPIRE` for PostgreSQL) |
| `SSL connection is required`, `TLS version mismatch`, `certificate verify failed` | TLS_CONFIG / TLS_CERT | Parameter group `rds.force_ssl` + `aws rds describe-db-engine-versions` for cert chain |
| `Connection refused`, `Can't connect to MySQL server`, TCP RST after SYN | INSTANCE_UNAVAILABLE / INSTANCE_FAILOVER / INSTANCE_MAINTENANCE | `aws rds describe-db-instances` (Status) + `aws rds describe-events` |
| `FATAL: too many connections`, `Too many connections` | CAPACITY_MAX_CONNECTIONS / CAPACITY_PROXY | Engine `SHOW STATUS LIKE 'Threads_connected'` + parameter `max_connections` |
| Connects but slow; query latency spike; reader lag | LATENCY_INSTANCE_CLASS / LATENCY_STORAGE / LATENCY_REPLICA_LAG | CloudWatch `CPUUtilization`, `DatabaseConnections`, Aurora `ReplicaLag`; Performance Insights |
| `Name or service not known`, `NXDOMAIN`, `server can't find` | DNS | `dig`/`nslookup` from caller; `aws route53 list-resource-record-sets` |
| None of the above, weird engine error, region-wide event | ESCALATE | `aws health describe-events` + AWS Service Health Dashboard |

## Pre-flight: instance state and gather-info gate

Before running symptom-specific probes, gather the canonical instance
metadata and short-circuit on instance states that mimic connectivity
failures. Misclassifying these produces hours of network debugging for a
problem that is not a network problem.

### Account-wide pre-flight commands

```bash
# 1. Instance state (Status, Endpoint, MultiAZ, SecurityGroups, SubnetGroup)
aws rds describe-db-instances --db-instance-identifier <id> --output json

# 2. Aurora: also fetch the cluster (writer/reader endpoints, failover state)
aws rds describe-db-clusters --db-cluster-identifier <cluster-id> --output json

# 3. Recent events (failover, maintenance, storage-full, engine restart)
aws rds describe-events --source-type db-instance --source-identifier <id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --output json

# 4. For Aurora: cluster-level events
aws rds describe-events --source-type db-cluster --source-identifier <cluster-id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --output json

# 5. AWS Health (regional events, scheduled maintenance on underlying host)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### Instance-state short-circuit

| `DBInstanceStatus` | Effect on diagnosis |
|---|---|
| `available` | Proceed with symptom-driven diagnosis. |
| `creating`, `modifying`, `backing-up`, `restoring`, `configuring-enhanced-monitoring`, `renaming`, `upgrading` | Instance is in a transitional state. Connections may succeed intermittently or fail with refused/timeout. Note in REMEDIATION; wait for `available` before drawing conclusions. |
| `rebooting`, `resetting-master-credentials` | Brief unavailability window (seconds to minutes). Connection refused during the window. Do NOT declare a network outage. |
| `inaccessible-encrypt-credentials` | KMS key inaccessible — the engine cannot decrypt storage. Connections fail at TLS/auth layer with misleading errors. Escalate to KMS, not network. ESCALATE. |
| `failed`, `incompatible-parameters`, `incompatible-restore`, `incompatible-network` | Instance is non-functional. The symptom looks like connectivity; the cause is engine state. ESCALATE for `failed`; for `incompatible-*`, plan parameter-group or restore fix. |
| `deleting`, `deleted` | Instance is gone or going. Reaching it is impossible by design; surface a different root cause (stale endpoint in the application config) and stop diagnosing. |
| `maintenance` | AWS is applying a patch during the maintenance window. Connection refused is expected. Wait for completion; do not declare an outage. |
| `storage-full` | Engine refuses new writes; some connections fail at auth or query time. The fix is storage expansion, not network. |
| `stopped`, `stopping` | Instance is intentionally offline. `start-db-instance` first. |

### Aurora-specific pre-flight

| Cluster field | Effect |
|---|---|
| `Status: available` + `MultiAZ: true` | Cluster is healthy at the cluster level. Continue diagnosis. |
| `Status: modifying` | A cluster-level modification is in flight (often a scaling or engine-version change). Reader/writer endpoints may briefly point to transitional instances. |
| `PendingModifiedValues` populated on cluster | A change is queued. Some read replicas may serve stale connections during apply. |
| `DBClusterMembers[].IsClusterWriter` flipped recently | Failover in progress or recently completed. Check `describe-events` for `Multi-AZ failover completed`. Client DNS cache is the most common cause of post-failover connection failures. |

If the input is malformed (missing `DBInstanceIdentifier`, absent symptom
description, no caller context for live diagnosis), emit:

```text
TARGET: <identifier or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum a symptom description
  and the DBInstanceIdentifier (or cluster identifier for Aurora). Cannot
  drive a diagnostic tree without the symptom layer.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string or
  observed symptom, (2) the DBInstanceIdentifier or cluster endpoint, and
  (3) for live diagnosis, the caller context (source subnet, security
  group, region, AZ).
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each layer
ends with either a positive root-cause confirmation (failing probe that
matches the symptom) or a pass that moves to the next layer. **Never emit
ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior RDS connectivity engineer knows
from incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **Security group references across VPCs do not resolve.** A SG rule that
  references `sg-xxx` works only when the source SG is in the SAME VPC. A
  cross-VPC caller (peered VPC, TGW-attached VPC) referenced by SG-id
  silently fails — the rule appears correct in the console but never
  matches inbound traffic. Cross-VPC callers must use CIDR blocks (or a
  referenced security group in the peered VPC, with peering enabled for
  the route). Operators who "see the SG allows sg-app" miss that sg-app is
  in a different VPC and the rule is dead.

- **NACLs are stateless; SGs are stateful.** A SG inbound allow on 3306
  implicitly allows the SYN-ACK back. A NACL inbound allow on 3306 also
  requires an outbound allow on the ephemeral range (1024-65535) because
  the return SYN-ACK is a separate NACL evaluation. The default NACL
  allows all traffic both ways; a custom NACL with a restrictive inbound
  list and a default outbound deny silently breaks the return path. Always
  evaluate the NACL in both directions for the connection's source port
  (ephemeral) and destination port (3306/5432/1433/1521/etc.).

- **`PubliclyAccessible: true` does NOT mean the instance is reachable
  from the public internet.** It means the instance has a public IP/route.
  The security group and NACL still gate inbound traffic. A public instance
  with SG 0.0.0.0/0 on 3306 is genuinely internet-exposed; a public
  instance with SG locked to a corporate CIDR is reachable only from that
  CIDR. Do NOT treat "PubliclyAccessible: true" as the cause of a timeout
  from an on-prem caller — verify the SG actually allows the caller's
  source IP.

- **Aurora writer and reader endpoints are DNS CNAMEs that flip on
  failover.** The writer endpoint (`<cluster>.cluster-on.aws`) always
  points to the current writer; the reader endpoint
  (`<cluster>.cluster-ro-on.aws`) load-balances across readers. On
  failover, the writer CNAME flips to a new IP. Clients that pin the
  resolved IP (some JDBC drivers, many ORM connection pools) continue
  connecting to the old (now-reader or down) IP. The fix is client-side:
  honor DNS TTL ≤ 30s, use the cluster endpoint (not instance endpoint),
  refresh the connection pool, and configure retry on `Connection refused`.

- **IAM database auth tokens expire after 15 minutes.** A connection pool
  that authenticates with an IAM token and holds the connection > 15 min
  does not see "auth failed" on a new query — the existing connection
  keeps working until the engine re-evaluates. New connections created
  from the cached token fail. Symptom pattern: "first N connections work,
  then suddenly auth fails." The fix is short connection lifetime (< 15
  min) or RDS Proxy (which manages credentials centrally).

- **`rds.force_ssl=1` (PostgreSQL) and `require_secure_transport=ON`
  (MySQL) reject plaintext connections AFTER the TCP handshake.** The
  symptom is "connection closes immediately after handshake" rather than
  timeout. Operators debug this as a network problem because the TCP
  layer succeeded. Check the parameter group, not the security group.

- **RDS TLS certificates rotated in 2024 (rds-ca-e2022 legacy) and 2025
  (rds-ca-e2024).** Clients pinned to rds-ca-2019 fail with "certificate
  verify failed" or "unable to get local issuer certificate" after an
  instance upgrade or maintenance window that picks up the new CA bundle.
  The fix is to update the client truststore with the new CA bundle
  BEFORE the instance rotates — rotate the client first, then the server.
  Reversing the order produces a multi-hour outage during which the
  network, SG, NACL, and auth layers all look clean.

- **`require_secure_transport=ON` for MySQL rejects non-TLS connections
  with a misleading error.** MySQL returns `Access denied` (error 1045)
  rather than a TLS error. Operators chase the credentials, reset the
  password, escalate to Secrets Manager — none of which helps. The
  diagnostic probe is `mysql --ssl-mode=REQUIRED`; if it succeeds where
  plaintext fails, the parameter is the cause.

- **Aurora Serverless v2 scaling latency looks like connection drops.**
  v2 scales capacity units (ACUs) up and down; at zero or near-zero ACUs,
  new connections take 10-30 seconds to be acknowledged. The pattern is
  "first connection after idle times out, retry succeeds." The fix is
  `MinCapacity` ≥ 0.5 (or higher for low-latency workloads), not network
  debugging.

- **Cross-Region Read Replicas use a region-scoped endpoint; the source
  region's DNS may not resolve it.** Applications in the source region
  that use the cross-region replica endpoint for DR-read see DNS failures
  if they don't have cross-region DNS resolution (Route 53 Resolver
  Rules, on-prem DNS forwarding). The fix is Route 53 Resolver or
  explicit cross-region DNS configuration, not instance debugging.

- **`max_connections` on Aurora is derived from the instance class, not a
  tunable.** Aurora computes `max_connections` as
  `GREATEST({log2(DBInstanceClassMemory/8186280128)}, 5000)` (engine-
  dependent formula). An operator who "sets max_connections = 2000" in a
  parameter group is overridden by the derived value. The symptom of
  hitting the derived cap looks identical to a configured cap — the fix
  is instance-class upsizing or RDS Proxy, not a parameter change.

- **RDS Proxy resolves connections through a proxy endpoint, which can
  confuse SG analysis.** The Proxy has its own security group; the
  instance's SG sees traffic from the Proxy's SG, not from the
  application's SG. Operators who "added sg-app to the instance SG" but
  see no effect are missing that the application connects to the Proxy,
  not the instance — the instance SG should allow the Proxy's SG.

- **Engine restarts during the maintenance window can look like rolling
  connectivity failures.** A Multi-AZ instance undergoing a minor-version
  upgrade in the maintenance window fails over (60-120s of connection
  drop), then back. Application sees two brief outages 10-20 minutes
  apart. The probe is `aws rds describe-events` for `Maintenance` and
  `DB instance restarted`; the fix is "wait," not "the network is
  flaky."

- **`pg_hba.conf` host rules on RDS for PostgreSQL are surfaced via the
  client certificate / IAM auth flags, not directly editable.** The
  PostgreSQL `pg_hba.conf` is managed by RDS — operators cannot edit it.
  "pg_hba.conf entry missing" on RDS is actually "IAM auth not enabled"
  or "the host rule requires TLS." The diagnostic is the parameter group,
  not `pg_hba.conf`.

### Step 1: Symptom entry — pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the seven categories, route to Step 9 (ESCALATE
or NEED_MORE_INFO).

| Symptom | Branch |
|---|---|
| Timeout (SYN never gets a SYN-ACK; tool reports `Connection timed out` or `Operation timed out`; `telnet <host> <port>` hangs) | Step 2 — Timeout |
| Authentication failed (TCP/TLS handshake completes; engine returns auth error) | Step 3 — Auth failed |
| TLS/SSL error (handshake reaches the TLS layer; `certificate verify failed`, `unsupported TLS version`, `SSL connection required`) | Step 4 — TLS |
| Connection refused (TCP RST after SYN; tool reports `Connection refused`, `Can't connect to MySQL server on`, `server closed the connection unexpectedly`) | Step 5 — Instance unavailable |
| Too many connections (engine returns `FATAL: too many connections` / `Too many connections` on connect) | Step 6 — Capacity |
| Connects but slow (latency spike, query timeouts, reader lag, intermittent success) | Step 7 — Latency |
| Hostname does not resolve (`NXDOMAIN`, `server can't find`, `Name or service not known`) | Step 8 — DNS |
| None of the above | Step 9 — Escalate / NEED_MORE_INFO |

### Step 2: Connection timeout — network-layer diagnostic tree

Symptom: SYN never receives a SYN-ACK. Tools report `Connection timed out`
or `Operation timed out`. `telnet <endpoint> <port>` hangs and eventually
times out. No engine error log entry (the engine never saw the connection).

Probe order (OSI-aligned; each layer must pass before the next):

#### 2a: Source-IP reachability check

```bash
# From the caller host (the EC2 instance / container / lambda where the app runs):
# Confirm the source IP the RDS instance will see
aws ec2 describe-network-interfaces \
  --filters Name=association:PublicIp,Values=<caller-public-ip> \
  --output json

# Or for private IP / cross-VPC:
aws ec2 describe-network-interfaces \
  --filters Name=private-ip-address,Values=<caller-private-ip> \
  --output json
```

The output identifies the caller's VPC, subnet, security group, and
attached NACL set. Capture these — every subsequent probe references them.

#### 2b: Security group inbound on the RDS instance

```bash
# Fetch the RDS instance's security groups
aws rds describe-db-instances --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0].VpcSecurityGroups[].VpcSecurityGroupId'

# For each SG, list the inbound rules
aws ec2 describe-security-groups --group-ids <sg-rds-1> <sg-rds-2> --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

**Match the caller's source against the inbound rules:**
- If the rule allows `0.0.0.0/0` on the engine port → SG allows.
- If the rule allows a CIDR — does the caller's source IP fall within it?
  - Caller in same VPC: use the caller's private IP.
  - Caller in peered VPC: use the caller's private IP in the peer VPC's CIDR.
  - Caller on-prem/over internet: use the caller's public IP or NAT EIP.
- If the rule references `sg-xxx` — is the source SG in the SAME VPC as
  the RDS SG? Cross-VPC SG references are silently ignored.
- If the rule references a prefix list — does the prefix list contain
  the caller's CIDR?

**Verdict:** if no inbound rule matches the caller's source IP/SG on the
engine port, **ROOT_CAUSE_FOUND** with `LAYER: NETWORK_SG`.

#### 2c: Security group outbound on the caller

SGs are stateful, but the caller still needs an outbound allow. The
default outbound (allow all) usually covers this, but a locked-down
caller SG can block the SYN.

```bash
aws ec2 describe-security-groups --group-ids <sg-caller> --output json | \
  jq '.SecurityGroups[].IpPermissionsEgress'
```

If the caller's egress does not allow traffic to the RDS instance's
private IP (or the RDS SG, if egress is SG-referenced), **ROOT_CAUSE_FOUND**
with `LAYER: NETWORK_SG` (caller-side).

#### 2d: NACL on the caller's subnet (stateless — check both directions)

```bash
aws ec2 describe-network-acls \
  --filters Name=association.subnet-id,Values=<caller-subnet-id> --output json | \
  jq '.NetworkAcls[].Entries'
```

**Inbound** (return SYN-ACK from RDS to caller's ephemeral port):
- Rule allow on the engine port from the RDS CIDR to the caller's
  ephemeral port range (1024-65535).
- Default NACL allows all; custom NACLs often miss this.

**Outbound** (initial SYN from caller to RDS engine port):
- Rule allow on the engine port to the RDS CIDR.

If either direction denies, **ROOT_CAUSE_FOUND** with `LAYER: NETWORK_NACL`.

#### 2e: NACL on the RDS instance's subnet

Same logic, mirrored. Fetch the NACL for the RDS subnet
(`DBSubnetGroup.Subnets[]`) and verify inbound on engine port + outbound
on ephemeral range. A common pattern is a custom NACL on the database
subnet that allows inbound on 3306 but has no explicit outbound allow on
the ephemeral range, silently dropping the SYN-ACK.

#### 2f: Route table — caller subnet

```bash
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<caller-subnet-id> --output json | \
  jq '.RouteTables[].Routes'
```

- For same-VPC: confirm a local route to the RDS VPC CIDR exists.
- For cross-VPC via peering: confirm a `pcx-xxx` peering route to the RDS
  VPC CIDR.
- For cross-VPC via Transit Gateway: confirm a `tgw-xxx` route.
- For internet path (caller is on-prem, RDS is public): confirm the
  route to the internet gateway (IGW).

If no route exists for the RDS endpoint's IP, **ROOT_CAUSE_FOUND** with
`LAYER: NETWORK_ROUTE`.

#### 2g: Route table — RDS subnet (return path)

Mirror of 2f for the RDS instance's subnet. The SYN-ACK must route back.
For cross-VPC, the RDS subnet's route table must have the peering/TGW
route back to the caller's VPC CIDR.

#### 2h: DB subnet group — multi-AZ coverage and AZ match

```bash
aws rds describe-db-subnet-groups --db-subnet-group-name <name> --output json
```

- Verify the subnet group has ≥2 AZs (Multi-AZ requirement).
- Verify the caller and the RDS instance share a route path (cross-AZ
  traffic within a VPC is allowed by default but incurs cross-AZ
  transfer cost; not a connectivity issue).
- If the subnet group has only one AZ and that AZ is degraded (AWS
  Health event), the instance is unreachable from cross-AZ callers in
  the same VPC only if the route table does not allow intra-VPC
  traffic (rare).

If the subnet group has no subnets in the caller's reachability scope,
**ROOT_CAUSE_FOUND** with `LAYER: NETWORK_SUBNET`.

#### 2i: Cross-VPC reachability

If the caller is in a different VPC:

```bash
# VPC peering
aws ec2 describe-vpc-peering-connections \
  --filters Name=requester-vpc-info.vpc-id,Values=<caller-vpc> \
            Name=status-code,Values=active --output json

# Transit Gateway
aws ec2 describe-transit-gateway-attachments \
  --filters Name=resource-id,Values=<caller-vpc> --output json

# Confirm both sides have routes referencing the peering/TGW
```

Common failures: peering connection is `pending-acceptance` (not active),
TGW route table does not propagate, requester/accepter route tables missing
the `pcx-`/`tgw-` route. If cross-VPC reachability is broken, **ROOT_CAUSE_FOUND**
with `LAYER: NETWORK_CROSS_VPC`.

#### 2j: After all network layers pass — final reachability probe

From the caller host:

```bash
# TCP reachability (should succeed if all above passed)
nc -vz <endpoint> <port>

# Or:
telnet <endpoint> <port>
```

If `nc -vz` succeeds but the application still times out, the issue is
likely client-side (connection pool, driver config, JVM DNS cache) —
emit ROOT_CAUSE_FOUND with `LAYER: UNKNOWN` and a client-side note, or
NEED_MORE_INFO if the caller context is incomplete.

### Step 3: Authentication failed — credentials and identity

Symptom: TCP and TLS succeed, but the engine returns an auth error.
Common strings: `FATAL: password authentication failed for user "X"`
(PostgreSQL), `Access denied for user 'X'@'Y' (using password: YES)`
(MySQL), `login failed for user 'X'` (SQL Server).

#### 3a: Master credentials match

```bash
# Fetch the master secret (if the app uses Secrets Manager)
aws secretsmanager get-secret-value --secret-id <secret-id> --output json | \
  jq '.SecretString | fromjson'

# Compare against what the application connection string uses
```

If the secret was recently rotated and the application still uses the
prior value, **ROOT_CAUSE_FOUND** with `LAYER: AUTH_CREDENTIALS`. Check
the Secrets Manager rotation Lambda's last successful run.

#### 3b: IAM database auth

```bash
# Is IAM auth enabled on the instance?
aws rds describe-db-instances --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0].IAMDatabaseAuthenticationEnabled'

# Generate an auth token to verify the IAM policy permits rds-db:connect
aws rds generate-db-auth-token \
  --hostname <endpoint> --port <port> --region <region> \
  --username <iam-mapped-user>
```

If IAM auth is enabled but token generation succeeds yet the engine still
rejects — verify the IAM policy includes `rds-db:connect` on the resource
`arn:aws:rds-db:<region>:<account>:dbuser:<resource-id>/<user>`. If the
policy is missing or scoped to the wrong resource, **ROOT_CAUSE_FOUND**
with `LAYER: AUTH_IAM`.

If IAM auth token worked initially but fails after ~15 minutes, it is
token expiry — the application is caching the token too long.
**ROOT_CAUSE_FOUND** with `LAYER: AUTH_IAM` (token expiry).

#### 3c: Password expired / account locked

For PostgreSQL:

```sql
-- Connect as master user; check the user's password expiry
SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname = '<user>';
```

For MySQL:

```sql
SELECT user, host, password_expired, account_locked FROM mysql.user WHERE user = '<user>';
```

If `password_expired = Y` or `rolvaliduntil < now()`, **ROOT_CAUSE_FOUND**
with `LAYER: AUTH_EXPIRED`.

#### 3d: pg_hba.conf and host rules (PostgreSQL)

On RDS, `pg_hba.conf` is not editable. The host rules that matter are
surfaced via `rds.force_ssl` (requires TLS for all connections) and IAM
auth (requires IAM token). If the symptom is `no pg_hba.conf entry for
host`, the actual cause is one of these — not a missing host rule. Probe
the parameter group:

```bash
aws rds describe-db-parameters --db-parameter-group-name <pg-name> --output json | \
  jq '.Parameters[] | select(.ParameterName == "rds.force_ssl")'
```

### Step 4: SSL/TLS errors

Symptom: TCP succeeds, TLS handshake fails. Common strings: `SSL
connection is required`, `certificate verify failed`, `unable to get
local issuer certificate`, `unsupported or disabled TLS version`,
`SSL/TLS handshake failed`.

#### 4a: Engine requires TLS

```bash
# MySQL
aws rds describe-db-parameters --db-parameter-group-name <pg-name> --output json | \
  jq '.Parameters[] | select(.ParameterName == "require_secure_transport")'

# PostgreSQL
aws rds describe-db-parameters --db-parameter-group-name <pg-name> --output json | \
  jq '.Parameters[] | select(.ParameterName == "rds.force_ssl")'
```

If `require_secure_transport=1` (MySQL) or `rds.force_ssl=1` (PostgreSQL)
and the client is connecting plaintext, **ROOT_CAUSE_FOUND** with
`LAYER: TLS_CONFIG`. Note: MySQL may surface this as `Access denied`
(error 1045), which is misleading — verify with `mysql --ssl-mode=REQUIRED`.

#### 4b: CA certificate bundle

```bash
# Inspect the engine version's CA
aws rds describe-db-engine-versions --engine <engine> --output json | \
  jq '.DBEngineVersions[] | select(.EngineVersion == "<version>") | .SupportedCACertificateIdentifiers'

# Current CA on the instance
aws rds describe-db-instances --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0].CACertificateIdentifier'
```

If the instance's CA is `rds-ca-e2024` (or newer) and the client truststore
only has `rds-ca-2019`, **ROOT_CAUSE_FOUND** with `LAYER: TLS_CERT`. The
fix is to update the client truststore to include the new CA bundle BEFORE
the instance rotates; if the rotation already happened, update the client
immediately.

#### 4c: TLS version mismatch

Some RDS engines enforce TLS 1.2 minimum (Aurora PostgreSQL 13+,
RDS PostgreSQL 14+); clients attempting TLS 1.0/1.1 fail the handshake.
The fix is client-side (Java: enable TLS 1.2 in the connection URL;
Python: `ssl_version=PROTOCOL_TLSv1_2`).

### Step 5: Connection refused — instance unavailable

Symptom: TCP SYN gets a RST (Connection refused). The host responds; the
port has no listener. Common cause: instance is down, failover in
progress, or maintenance window.

```bash
# Instance state
aws rds describe-db-instances --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0] | {DBInstanceStatus, MultiAZ, LatestRestorableTime}'

# Recent events (failover, maintenance, restart, storage-full)
aws rds describe-events --source-type db-instance --source-identifier <id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --output json
```

| Event | Verdict and layer |
|---|---|
| `Multi-AZ failover started` / `Multi-AZ failover completed` within last 5 min | ROOT_CAUSE_FOUND, `LAYER: INSTANCE_FAILOVER`. Wait for failover completion; expect 60-120s of connection drop. |
| `DB instance restart` / `DB instance shutdown` | ROOT_CAUSE_FOUND, `LAYER: INSTANCE_MAINTENANCE`. Wait for the instance to return to available. |
| `Maintenance window` event | ROOT_CAUSE_FOUND, `LAYER: INSTANCE_MAINTENANCE`. Maintenance in progress; wait. |
| `DB instance storage full` | ROOT_CAUSE_FOUND, `LAYER: INSTANCE_STORAGE_FULL`. Modify storage: `aws rds modify-db-instance --allocated-storage <new> --apply-immediately`. |
| Status `deleting`, `failed`, `incompatible-*` | ESCALATE. The instance is not coming back without intervention. |
| No events, status `available`, port mismatch | Verify the application connects to the correct port. Engine port by default: MySQL 3306, PostgreSQL 5432, SQL Server 1433, Oracle 1521, MariaDB 3306. Aurora uses the engine's default. A custom port configured on the instance must be reflected in the application's connection string. |

### Step 6: Too many connections — capacity exhaustion

Symptom: engine returns `FATAL: too many connections` (PostgreSQL),
`Too many connections` (MySQL), or login refused with capacity reason.

```bash
# Current connection count (requires database admin access)
# PostgreSQL:
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;

# MySQL:
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Threads_connected';
```

For Aurora, `max_connections` is derived from the instance class:

```text
Aurora MySQL: GREATEST({log2(DBInstanceClassMemory/8186280128)}, 5000)
Aurora PostgreSQL: GREATEST({GREATEST({DBInstanceClassMemory/9531392},5000)},{DBInstanceClassMemory/16106127360})
```

The parameter group cannot override the derived value below the floor.

**Verdicts:**
- Existing connections hit `max_connections` (RDS): ROOT_CAUSE_FOUND,
  `LAYER: CAPACITY_MAX_CONNECTIONS`. Fix: raise `max_connections`
  parameter (apply-immediate), upsize instance class, or add RDS Proxy.
- Existing connections hit Aurora derived cap: ROOT_CAUSE_FOUND,
  `LAYER: CAPACITY_MAX_CONNECTIONS`. Fix: upsize instance class
  (parameter cannot raise above the derived value) or add RDS Proxy.
- Connection pool in the application is exhausting its own limit (engine
  is below max_connections): ROOT_CAUSE_FOUND, `LAYER: CAPACITY_PROXY`
  (recommend RDS Proxy or pool tuning). Probe with `pg_stat_activity` /
  `SHOW PROCESSLIST` to identify long-idle connections pinning the pool.
- Aurora Serverless v2 hitting max-connections scaling cap: ROOT_CAUSE_FOUND,
  `LAYER: CAPACITY_PROXY`. Raise `MaxCapacity` on the cluster.

### Step 7: Connects but slow — latency

Symptom: connections succeed, but query latency is elevated, queries time
out at the application layer, or read replicas lag behind the writer.

```bash
# CloudWatch metrics — instance-level
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=<id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# Aurora replica lag
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name AuroraReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=<reader-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# Performance Insights
aws pi describe-dimension-keys \
  --service-type RDS --identifier <dbi-resource-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --metric db.load.avg --group-by db.sql --output json
```

**Verdicts:**
- CPU sustained > 85% on the instance: ROOT_CAUSE_FOUND,
  `LAYER: LATENCY_INSTANCE_CLASS`. Fix: upsize instance class (m5 → m5.2xlarge
  or memory-optimized class for buffer-cache workloads); investigate top
  SQL via Performance Insights.
- Storage type: gp2 with high IOPS demand hitting the burst-bucket
  depletion pattern (IOPS drops to baseline after burst credits exhaust):
  ROOT_CAUSE_FOUND, `LAYER: LATENCY_STORAGE`. Fix: migrate to gp3 with
  provisioned IOPS, or io2/io2 Block Express for predictable latency.
- Aurora replica lag > several seconds sustained: ROOT_CAUSE_FOUND,
  `LAYER: LATENCY_REPLICA_LAG`. Causes: writer throughput exceeds replica
  capacity (upsizing the replica or scaling Aurora Serverless v2),
  long-running transactions on the writer, replica in a different region
  (cross-region replication lag inherent).
- Burstable t-family CPU credit exhaustion (CPUUtilization low but
  BurstBalance near 0): ROOT_CAUSE_FOUND, `LAYER: LATENCY_INSTANCE_CLASS`.
  Fix: switch to non-burstable (m-class) or enable Unlimited mode.

### Step 8: DNS resolution failure

Symptom: hostname does not resolve. Tools report `NXDOMAIN`,
`server can't find`, `Name or service not known`.

```bash
# From the caller host
nslookup <endpoint>
dig <endpoint>

# Route 53 records (custom domains pointing at RDS)
aws route53 list-resource-record-sets --hosted-zone-id <hz-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Name | test("<domain>"))'

# Verify the RDS endpoint resolves at all
aws rds describe-db-instances --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0].Endpoint | {Address, Port, HostedZoneId}'
```

**Verdicts:**
- RDS endpoint itself does not resolve from the caller: the caller's DNS
  (DHCP options set VPC DNS) is broken or the endpoint was deleted with
  the instance. ROOT_CAUSE_FOUND, `LAYER: DNS`.
- Custom domain (Route 53 CNAME) pointing at the wrong endpoint: the
  CNAME target is stale (points to a deleted instance or wrong region).
  ROOT_CAUSE_FOUND, `LAYER: DNS`. Fix the CNAME target.
- Cross-Region endpoint not resolvable from the source region's VPC: the
  VPC does not have cross-region DNS resolution. ROOT_CAUSE_FOUND,
  `LAYER: DNS`. Fix: Route 53 Resolver Rules, peering with DNS resolution
  enabled, or explicit cross-region DNS forwarding.

### Step 9: Escalate or NEED_MORE_INFO

If none of the above produced a positive root-cause match, OR the symptom
clearly indicates an AWS-side incident (region event, KMS outage,
unreachable KMS key, status `failed`), emit one of:

- **ESCALATE** — AWS-side incident. Surface the AWS Health event ARN, the
  instance status, and the relevant CloudTrail error. Recommend opening
  a Support case. Do NOT continue diagnosing; the cause is outside the
  customer's control.
- **NEED_MORE_INFO** — A specific probe requires operator input. List the
  missing pieces (caller context, application logs, exact error string,
  Secrets Manager permission scope) and the next probe to run once the
  info is available.

## Output format

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
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <id> in <region>. Proceed?
  (yes/no)"
```

### Worked example — connection timeout, missing SG rule

```text
TARGET: db-prod-mysql
VERDICT: ROOT_CAUSE_FOUND
REASON: The RDS security group sg-rds-prod has no inbound rule matching
  the caller's source IP 10.42.5.10 on port 3306 — the SYN is dropped at
  the instance's security group (Step 2b).
LAYER: NETWORK_SG
EVIDENCE:
  - Symptom: application on i-app-server (10.42.5.10) reports "Operation
    timed out" when connecting to db-prod-mysql:3306. telnet hangs.
  - Probe: aws ec2 describe-security-groups --group-ids sg-rds-prod
    returns inbound rules allowing 10.42.0.0/24 (not 10.42.5.10) and
    sg-app-old (a deleted SG). No rule matches 10.42.5.10.
  - Passing: route table for subnet-bbb has a local route to the RDS
    CIDR; NACL is the default VPC NACL (allow all); the caller's SG
    egress allows all; nc -vz from a known-good host in 10.42.0.0/24
    succeeds.
REMEDIATION:
  1. Add an inbound rule to sg-rds-prod allowing the caller's subnet
     (preferred over the specific IP for tolerance to instance moves):
     aws ec2 authorize-security-group-ingress --group-id sg-rds-prod
       --protocol tcp --port 3306 --cidr 10.42.5.0/24 --profile <p>
  2. Verify from the caller: nc -vz db-prod-mysql.cid.on.aws 3306
     (should now succeed within 1s).
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to authorize-security-group-ingress on sg-rds-prod in
   us-east-1 for 10.42.5.0/24 on tcp/3306. Proceed? (yes/no)"
```

### Worked example — auth failed, IAM token expired

```text
TARGET: db-prod-postgres
VERDICT: ROOT_CAUSE_FOUND
REASON: Application uses IAM database auth with a connection pool that
  caches tokens > 15 minutes; new connections created after the token
  TTL fail with "FATAL: password authentication failed" (Step 3b).
LAYER: AUTH_IAM
EVIDENCE:
  - Symptom: first ~50 connections succeed each morning; subsequent
    connections fail with "password authentication failed for user
    'iam_app_role'". Database logs show no password change.
  - Probe: aws rds describe-db-instances confirms
    IAMDatabaseAuthenticationEnabled: true.
  - Probe: aws rds generate-db-auth-token succeeds and produces a valid
    token; connecting with the fresh token works. Connecting with the
    application's existing token fails.
  - Passing: SG, NACL, route table all pass; TLS handshake completes.
REMEDIATION:
  1. Reduce the application's connection pool max-lifetime to < 14
     minutes (e.g. HikariCP maxLifetime=PT10M, or RDS connection
     injection of a refreshed token).
  2. Or migrate the application to RDS Proxy, which manages IAM auth
     credentials centrally so the application never sees token expiry.
  3. Verify by tailing the application logs for 30+ minutes after the
     change; no new auth-failed errors should appear.
```

### Worked example — Multi-AZ failover in progress (ESCALATE)

```text
TARGET: db-prod-mysql
VERDICT: ESCALATE
REASON: Instance is mid Multi-AZ failover; connection refused is the
  expected behaviour during standby promotion. Customer-side action
  cannot accelerate the failover. AWS-side event should complete within
  60-120 seconds (Step 5).
LAYER: INSTANCE_FAILOVER
EVIDENCE:
  - aws rds describe-db-instances returns DBInstanceStatus: modifying.
  - aws rds describe-events returns "Multi-AZ failover started" 45
    seconds ago.
  - No SG/NACL/route change in the last 24 hours.
REMEDIATION:
  1. Wait 60-120 seconds for failover to complete; re-probe with
     aws rds describe-events for "Multi-AZ failover completed".
  2. After completion, monitor application for client-DNS-cache
     failures (JVM networkaddress.cache.ttl). Restart application
     processes if they pin the old writer IP.
  3. If the failover does not complete within 5 minutes, open a Support
     case and surface the instance identifier and event timestamp.
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches
  the symptom. A "process of elimination" diagnosis (the SG must be the
  issue because the rest looks fine) erodes operator trust when the real
  cause is elsewhere.

- NEVER skip the OSI order for timeout symptoms. If you check the
  security group before the route table and conclude "the SG is fine,
  must be the instance," you missed that the route table has no route
  for the RDS CIDR — the SYN never reached the SG evaluation.

- NEVER evaluate NACLs in only one direction. NACLs are stateless; the
  return SYN-ACK is a separate evaluation. The most common NACL mistake
  is an inbound rule on 3306 with no outbound rule on the ephemeral
  range (1024-65535).

- NEVER assume a security-group reference (`sg-xxx`) works cross-VPC.
  Cross-VPC SG references are silently ignored. Use CIDR blocks or a
  referenced SG in the peered VPC (with peering connection in the route
  table).

- NEVER treat `PubliclyAccessible: true` as the cause of a timeout from
  an on-prem caller. The flag means the instance has a public IP; the
  security group still gates traffic. Verify the SG allows the caller's
  public IP before declaring the flag the cause.

- NEVER reset the master password when the symptom is an IAM-auth token
  expiry. The error string ("password authentication failed") looks
  identical; the cause and fix are completely different. Check
  `IAMDatabaseAuthenticationEnabled` and the application's connection
  lifetime before touching the password.

- NEVER treat MySQL `Access denied` (error 1045) as a credentials
  problem when `require_secure_transport=1`. MySQL surfaces the TLS
  requirement as a generic 1045 error. Verify with `mysql
  --ssl-mode=REQUIRED` before resetting credentials.

- NEVER update only the RDS CA bundle on the client side and assume
  connectivity is restored. The new CA bundle contains both the old and
  new CAs; the instance must also be set to the matching CA. If the
  instance was already rotated to `rds-ca-e2024` and the client has only
  `rds-ca-2019`, the client update is mandatory and the instance does
  not need to rotate back.

- NEVER treat Aurora Serverless v2 connection drops as a network
  problem. Scaling from zero ACUs introduces 10-30s of connection
  acknowledgement latency. The fix is `MinCapacity`, not network
  debugging.

- NEVER raise `max_connections` on Aurora in a parameter group to
  address "too many connections." Aurora derives the value from the
  instance class; the parameter is overridden. The fix is instance-class
  upsizing or RDS Proxy.

- NEVER chase a Cross-Region Read Replica DNS failure as an instance
  problem. Cross-region endpoints require cross-region DNS resolution;
  the source VPC's DNS may not resolve the destination region's
  endpoint. Fix Route 53 Resolver Rules or peering DNS settings.

- NEVER recommend modifying an instance in `deleting`, `failed`,
  `incompatible-*`, or `storage-full` status without addressing the
  underlying state. `modify-db-instance` against these states either
  fails or compounds the issue.

- NEVER declare "the network is flaky" without running `nc -vz` or
  equivalent from the caller host at least three times. Intermittent
  packet loss is rare in VPC; intermittent failures are usually
  capacity (connection pool), failover (DNS cache), or scaling
  (Aurora Serverless v2 cold start).

- NEVER skip `aws rds describe-events` when diagnosing connection
  refused. Failover, maintenance, and storage-full events explain the
  majority of refused-connection incidents. Without events, you will
  waste time on SG and NACL probes for an instance that is mid-restart.

- NEVER assume the application connects to the cluster endpoint. Many
  applications are configured with the instance endpoint (which does not
  follow failover) rather than the cluster endpoint (which does). After
  a failover, instance-endpoint clients continue connecting to the
  now-demoted reader. The fix is the cluster endpoint in the connection
  string.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`authorize-security-group-ingress`, `modify-db-instance`,
  `modify-db-cluster`, `reboot-db-instance`), emit and await operator
  approval. Do NOT execute the CLI until the operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is read-only
  (`describe-*`, `dig`, `nc -vz`, CloudWatch `get-metric-statistics`).
  Do not perform state-changing operations as diagnostic probes.

- **SG changes should prefer CIDR over specific IP** for tolerance to
  instance moves within the subnet, but never expand the scope to
  `0.0.0.0/0` to "fix" a connectivity issue — that exposes the database
  to the internet. If the caller is in a peered VPC, use the peered-VPC
  CIDR.

- **`modify-db-instance --apply-immediately` for `max_connections`** is
  safe and does not cause downtime. For `--instance-class` and
  `--storage-type`, prefer the maintenance window; the change causes a
  brief restart or I/O suspension.

- **RDS Proxy creation is non-disruptive** but the application's
  connection string must be updated to point at the Proxy endpoint, not
  the instance endpoint. Plan the cutover; do not flip in the middle of
  a traffic peak.

- **Engine password reset (`modify-db-instance --master-user-password`)
  is destructive.** It changes the password the application uses. Only
  perform after confirming the current password is genuinely wrong (not
  IAM-auth expiry, not TLS issue). Reset via Secrets Manager rotation
  where possible, not `--master-user-password`.

- **CA certificate rotation is a cutover, not a flag.** Update the
  client truststore first, then rotate the instance's CA. Reversing the
  order produces a multi-hour outage for any client pinned to the prior
  CA.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple instances (e.g., a missing SG rule
  applied to a fleet), batch remediation into groups of at most 5
  instances, emit a single CONFIRM per batch, and verify between batches.

## Remediation guidance

### For NETWORK_SG — missing or mis-scoped inbound rule

1. Add the rule with the narrowest scope that covers legitimate callers:
   ```bash
   aws ec2 authorize-security-group-ingress --group-id <sg-rds>
     --protocol tcp --port <engine-port> --cidr <caller-cidr>
   ```
2. Prefer a referenced SG (same-VPC) or prefix list (managed CIDR list)
   over a raw CIDR — both are easier to maintain.
3. Verify from the caller with `nc -vz <endpoint> <port>`.

### For NETWORK_NACL — stateless rule missing

1. Add the inbound rule on the engine port from the caller CIDR.
2. Add the outbound rule on the ephemeral port range (1024-65535) to the
   caller CIDR (this is the rule most commonly missing).
3. Verify with `nc -vz` from the caller.

### For NETWORK_ROUTE — route table missing the route

1. Add the route: `aws ec2 create-route --route-table-id <rtb>
   --destination-cidr-block <rds-cidr> --vpc-peering-connection-id <pcx>`
   (or `--transit-gateway-id <tgw>` / `--gateway-id <igw>`).
2. Verify the return route exists in the RDS subnet's route table.

### For NETWORK_SUBNET — subnet group issue

1. If the subnet group has only one subnet/AZ, add a second:
   `aws rds modify-db-subnet-group --db-subnet-group-name <name>
   --subnet-ids <new-subnet-id>`.
2. If the instance is in an AZ with no caller route path, modify the
   instance to move AZs (Multi-AZ failover can move the writer).

### For NETWORK_CROSS_VPC — peering/TGW not active

1. Accept the peering connection (accepter side): `aws ec2
   accept-vpc-peering-connection --vpc-peering-connection-id <pcx>`.
2. Add routes on BOTH VPCs' route tables referencing the peering
   connection.
3. For TGW: verify the TGW route table propagates the attachment.

### For AUTH_CREDENTIALS — credentials mismatch

1. Update the application's secret (Secrets Manager rotation or manual
   update): `aws secretsmanager put-secret-value --secret-id <id>
   --secret-string '<json>'`.
2. Restart the application processes that cached the prior credential.
3. Verify by connecting with the new credential from the caller host.

### For AUTH_IAM — IAM database auth issue

1. If the IAM policy is missing `rds-db:connect`, attach a policy with:
   ```json
   {"Effect": "Allow", "Action": "rds-db:connect",
    "Resource": "arn:aws:rds-db:<region>:<account>:dbuser:<resource-id>/<user>"}
   ```
2. If the symptom is token expiry, reduce the connection pool
   max-lifetime or migrate to RDS Proxy.

### For AUTH_EXPIRED — password expired or account locked

1. Reset the password: PostgreSQL `ALTER USER <user> PASSWORD '<new>';
   ALTER USER <user> VALID UNTIL 'infinity';`. MySQL `ALTER USER '<user>'
  @'%' IDENTIFIED BY '<new>' PASSWORD EXPIRE NEVER; ACCOUNT UNLOCK;`.
2. Verify with a fresh connection.

### For TLS_CONFIG — engine requires TLS but client connects plaintext

1. Update the client connection string to require TLS:
   - MySQL: `jdbc:mysql://...?useSSL=true&requireSSL=true`
   - PostgreSQL: `jdbc:postgresql://...?sslmode=require`
   - Python (psycopg2): `sslmode='require'`
2. Verify with `mysql --ssl-mode=REQUIRED` or `psql "sslmode=require ..."`.

### For TLS_CERT — CA bundle mismatch

1. Download the new CA bundle from
   https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html
2. Update the client truststore (Java: `keytool -importcert -alias
   rds-ca-e2024 -file rds-combined-ca-bundle.pem -keystore truststore.jks`).
3. Verify with a fresh connection.

### For INSTANCE_FAILOVER — wait

1. Wait for `aws rds describe-events` to show "Multi-AZ failover completed."
2. After completion, restart application processes that pin the old
   writer IP (or wait for the JVM DNS cache TTL to expire).
3. If failover does not complete within 5 minutes, escalate to Support.

### For INSTANCE_MAINTENANCE — wait

1. Wait for the maintenance window to complete.
2. Verify the instance returns to `available` status.

### For INSTANCE_STORAGE_FULL — expand storage

```bash
aws rds modify-db-instance --db-instance-identifier <id>
  --allocated-storage <new-size> --apply-immediately --profile <p>
```

Note: storage expansion is online for gp3 and io2; the volume becomes
available within minutes. For magnetic or legacy types, a brief
interruption may occur.

### For CAPACITY_MAX_CONNECTIONS — raise the limit or add RDS Proxy

- RDS: `aws rds modify-db-instance --db-instance-identifier <id>
  --max-connections <new> --apply-immediately` (via parameter group
  apply, not direct modify).
- Aurora: upsize the instance class (derived cap rises accordingly).
- All engines: add RDS Proxy to pool and reuse connections.

### For LATENCY_INSTANCE_CLASS — upsize or change family

```bash
aws rds modify-db-instance --db-instance-identifier <id>
  --db-instance-class <new-class> --profile <p>
```
Omit `--apply-immediately` to run in the maintenance window. The change
causes a brief restart.

### For LATENCY_STORAGE — migrate to gp3 or io2

```bash
aws rds modify-db-instance --db-instance-identifier <id>
  --storage-type gp3 --iops <provisioned> --profile <p>
```
For Aurora, storage is cluster-managed and cannot be changed per
instance.

### For LATENCY_REPLICA_LAG — upsize replica or reduce writer load

1. Identify long-running transactions on the writer via Performance
   Insights.
2. Upsize the replica instance class.
3. For Aurora Serverless v2, raise the replica's `MaxCapacity`.

### For DNS — fix the resolution path

- Route 53 CNAME stale: update the record to point at the current RDS
  endpoint.
- VPC DNS failure: verify the DHCP options set points at
  AmazonProvidedDNS (169.254.169.253); restart the VPC DNS service if
  degraded.
- Cross-Region: configure Route 53 Resolver Rules or peering DNS.

## Deep reference: RDS connectivity layer model

### Layer ordering for timeout symptoms (strict OSI)

```
DNS resolution     (L7)   →  does the hostname resolve?
Routing            (L3)   →  does the route table have a route?
SG (caller egress) (L4)   →  does the caller's SG allow the SYN out?
SG (RDS ingress)   (L4)   →  does the RDS SG allow the SYN in?
NACL (caller)      (L4)   →  both directions: SYN out, SYN-ACK back
NACL (RDS subnet)  (L4)   →  both directions: SYN in, SYN-ACK out
Subnet/AZ          (L2)   →  is the subnet reachable from the caller?
Cross-VPC          (L3)   →  is peering/TGW active and routed?
Port reachability  (L4)   →  does nc -vz succeed?
TLS handshake      (L5-6) →  does the TLS negotiation complete?
Auth               (L7)   →  does the engine accept the credentials?
```

Skipping a layer produces false root causes. Always probe in order.

### Aurora endpoint model

| Endpoint | Format | Behaviour |
|---|---|---|
| Cluster writer | `<cluster>.cluster-on.aws` | Points to the current writer; flips on failover. Recommended for write traffic. |
| Cluster reader | `<cluster>.cluster-ro-on.aws` | Load-balances across reader instances. Recommended for read traffic. |
| Instance | `<instance>.on.aws` | Points to a specific instance; does NOT follow failover. Use only for administrative singletons. |
| Custom | `<custom>.<domain>` | Route 53 CNAME pointing at any of the above. |
| Cross-Region | Same `<cluster>.on.aws` shape in the destination region | Resolves only within the destination region (or with cross-region DNS). |

### Aurora `max_connections` derivation (engine-dependent formulas)

```
Aurora MySQL:      GREATEST({log2(DBInstanceClassMemory/8186280128)}, 5000)
Aurora PostgreSQL: GREATEST({GREATEST({DBInstanceClassMemory/9531392},
                            5000)},
                          {DBInstanceClassMemory/16106127360})
```

Approximate derived caps by instance class (Aurora MySQL):

| Instance class | Memory (GB) | Derived max_connections |
|---|---|---|
| db.r6i.large | 16 | ~6,000 |
| db.r6i.2xlarge | 64 | ~13,000 |
| db.r6i.4xlarge | 128 | ~14,000 |
| db.r6i.8xlarge | 256 | ~15,000 |
| db.r6i.16xlarge | 512 | ~16,000 |

The formula floors at 5,000 (Aurora MySQL) or 5,000 (Aurora PostgreSQL).
Parameter-group overrides cannot raise above the derived value.

### IAM database auth token lifetime

- Token validity: 15 minutes from issuance.
- Token scope: region + endpoint + database user.
- Token format: SigV4-signed HTTPS-style URL (not a JWT).
- Token caching rules:
  - The AWS SDK generates a fresh token per `generate-db-auth-token` call.
  - Applications MUST NOT cache tokens longer than 14 minutes.
  - Connection pools that hold connections > 15 min MUST either refresh
    the token before each new connection or migrate to RDS Proxy.

### RDS Proxy connection handling

- The Proxy terminates the client TLS handshake and presents a stable
  endpoint to the application.
- The Proxy opens a pool of backend connections to the RDS instance,
  reusing them across application requests.
- IAM auth credentials are managed by the Proxy — the application sees
  no token expiry.
- The Proxy's SG is the source the instance sees; the instance's SG must
  allow the Proxy's SG, not the application's SG.

### CA certificate rotation timeline

| CA identifier | Active from | Notes |
|---|---|---|
| rds-ca-2019 | 2019 | Deprecated; clients should migrate. |
| rds-ca-e2022 (legacy) | 2022 | Still valid for existing instances. |
| rds-ca-e2024 | 2024 | Default for new instances from late 2024. |
| rds-ca-rsa2048-g1 | 2022 | RSA alternative. |
| rds-ca-rsa4096-g1 | 2023 | Stronger RSA. |
| rds-ca-ecc384-g1 | 2023 | ECDSA. |

Always rotate the client truststore BEFORE rotating the instance's CA.
Reversing the order produces a multi-hour outage.

## Recent AWS features (2024-2026)

- **RDS Proxy IAM auth enhancements (2024):** Improved IAM auth handling
  for Proxy endpoints, including automatic token refresh. Auditors should
  recommend Proxy for any application with IAM-auth-related pool issues.
- **Aurora Serverless v2 scaling improvements (2024-2025):** Faster
  scaling from zero; reduced cold-start latency. `MinCapacity` ≥ 0.5 is
  recommended for low-latency workloads; zero-capacity introduces 10-30s
  acknowledgement latency.
- **RDS TLS 1.3 enforcement (2024-2025):** Aurora PostgreSQL 16+ and RDS
  PostgreSQL 14+ enforce TLS 1.2 minimum. Clients on TLS 1.0/1.1 fail
  the handshake.
- **gp3 default for new RDS instances (2024):** New instances default to
  gp3 storage with 3000 IOPS / 125 MiB/s baseline. IOPS-heavy workloads
  should provision additional IOPS above the baseline.
- **Cross-Region read replica enhancements for Aurora Global Database
  (2025):** Reduced replication lag and faster cross-region failover.
  Auditors should verify Route 53 health checks and cross-region DNS
  resolution for Global Database clusters.
- **RDS Blue/Green deployments for major version upgrades (2024-2025):**
  Reduces connection-outage windows during major-version upgrades; the
  switch at the endpoint layer is sub-minute. Plan client DNS TTL ≤ 30s
  to maximize benefit.

## Domain

AWS CloudOps / RDS & Aurora Connectivity, Networking, Authentication,
and Incident Diagnosis.

## AWS documentation

- **Amazon RDS User Guide — Connecting to a DB instance** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_CommonTasks.Connect.html
- **RDS security groups** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.RDSSecurityGroups.html
- **IAM database authentication** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html
- **Using SSL/TLS to encrypt a connection** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html#PostgreSQL.Concepts.General.SSL
- **Aurora endpoints** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html
- **Amazon RDS API Reference** — https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/
- **AWS CLI RDS reference** — https://docs.aws.amazon.com/cli/latest/reference/rds/
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
