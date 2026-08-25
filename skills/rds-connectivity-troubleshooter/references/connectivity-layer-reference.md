# RDS Connectivity Layer Reference Guide

Supplementary reference for the RDS Connectivity Troubleshooter skill.
This is loaded on-demand when a diagnostic needs engine-specific port
numbers, NACL/SG evaluation rules, or Aurora endpoint semantics.

## Engine port registry

### Common RDS engines

| Engine | Default port | Notes |
| --- | --- | --- |
| MySQL | 3306 | Default; configurable via `--port` on instance creation |
| MariaDB | 3306 | Same as MySQL |
| PostgreSQL | 5432 | Default; configurable |
| Aurora MySQL | 3306 | Cluster-scoped port |
| Aurora PostgreSQL | 5432 | Cluster-scoped port |
| SQL Server | 1433 | Default for the engine; Web/Express/Standard/Enterprise |
| Oracle | 1521 | Default for TNS listener |
| Oracle (RMAN) | 1521 | Same listener, different SID/service |
| Db2 | 50000 | Default DB2 port |

### Custom ports

RDS allows custom port assignment at instance creation. The instance's
port is exposed in `Endpoint.Port` from `describe-db-instances`. Security
group rules and NACLs MUST reference the actual port — operators who
copy-paste the default-port rule into a custom-port instance silently
drop traffic.

### Aurora cluster port

For Aurora, the port is cluster-scoped (set at cluster creation). All
instances in the cluster use the same listener port.

## TCP reachability probe matrix

Use these probes from the caller host (the EC2 instance / container /
Lambda function where the application runs):

| Probe | What it tells you | Pass result | Fail result |
| --- | --- | --- | --- |
| `dig <endpoint>` / `nslookup <endpoint>` | DNS resolution | IP returned | NXDOMAIN (DNS issue) |
| `nc -vz <endpoint> <port>` (or `telnet`) | TCP reachability | Connected | Timeout (network) or refused (instance down) |
| `mysql -h <endpoint> -u <user> -p --ssl-mode=REQUIRED` | Engine handshake | Connected / auth error | Handshake fails (TLS or auth layer) |
| `psql "host=<endpoint> sslmode=require"` | Engine handshake | Connected / auth error | Handshake fails (TLS or auth layer) |
| `aws rds generate-db-auth-token --hostname <endpoint>` | IAM auth token generation | Token returned | IAM policy missing |

Probe order: DNS → TCP → TLS → Auth. Each layer must pass before the next.

## Security group evaluation rules

### Stateful (SG)

- An inbound allow implicitly allows the return traffic on the same
  connection.
- Outbound rules are independent (default allow-all egress is typical).
- Source can be: CIDR, referenced SG (same VPC), or prefix list.
- Cross-VPC SG references are silently ignored — use CIDR or a
  referenced SG in the peered VPC.

### Stateless (NACL)

- Each direction is evaluated independently.
- Inbound allow on the engine port ALSO requires outbound allow on the
  caller's ephemeral port range (1024-65535) for the SYN-ACK.
- Rule numbers are evaluated lowest-to-highest; first match wins.
- Default rule `*` (DENY ALL) is implicit if no explicit allow matches.

### Common SG/NACL patterns that break connectivity

| Pattern | Symptom |
| --- | --- |
| SG inbound rule references `sg-xxx` from a different VPC | SYN dropped silently |
| NACL inbound allow on 3306, outbound deny on ephemeral | SYN-ACK dropped |
| NACL outbound allow on 3306 only, no ephemeral allow on inbound | SYN out but SYN-ACK dropped on return evaluation |
| SG inbound allows 0.0.0.0/0 but PubliclyAccessible is false | Source IP is private, not public — 0.0.0.0/0 rule doesn't help |
| SG egress rule was tightened to specific CIDR | SYN never leaves the caller |

## Aurora endpoint behaviour reference

### Failover semantics

| Endpoint type | Behaviour on failover |
| --- | --- |
| Cluster writer | DNS CNAME flips to the new writer instance; TTL 30s |
| Cluster reader | Load-balancing re-balances across surviving readers |
| Instance | Does NOT follow failover; still points at the original instance (now a reader or down) |

### Client DNS cache traps

| Client / driver | Default DNS TTL | Fix |
| --- | --- | --- |
| JVM (Java) | 60s (`networkaddress.cache.ttl=60`) | Set `networkaddress.cache.ttl=30` in `$JAVA_HOME/lib/security/java.security` or `-Dnetworkaddress.cache.ttl=30` |
| Python (socket.getaddrinfo) | Process-lifetime (until refreshed) | Use a connection pool that refreshes; or restart workers periodically |
| Node.js (dns.lookup default) | OS resolver cache | Use `dns.lookup` with `{ttl: true}` and refresh |
| HikariCP (Java) | Pool holds connections by IP; pool-idle timeout controls refresh | Set `maxLifetime` ≤ 28s to force refresh after a failover |
| Go database/sql | Each connection resolves at open | Set `ConnMaxLifetime` ≤ 30s |

## Aurora Serverless v2 capacity and latency

| Setting | Effect on connectivity |
| --- | --- |
| `MinCapacity: 0` | Cold-start latency 10-30s on first connection after idle |
| `MinCapacity: 0.5` | Some warm capacity; first connection still has small latency |
| `MinCapacity: 1+` | Fully warm; no cold-start latency |
| `MaxCapacity < required` | New connections refused when capacity cap is reached |

## IAM database auth — region and resource format

### Resource ARN for `rds-db:connect`

```
arn:aws:rds-db:<region>:<account>:dbuser:<db-instance-resource-id>/<db-user>
```

For Aurora clusters:

```
arn:aws:rds-db:<region>:<account>:dbuser:<db-cluster-resource-id>/<db-user>
```

The `db-instance-resource-id` (e.g., `db-AAAAAABBCCCDDD`) is the
`DbiResourceId` from `describe-db-instances`, NOT the
`DBInstanceIdentifier` (e.g., `db-prod-mysql`). Using the wrong ID in the
IAM policy produces "auth failed" that looks identical to a credentials
problem.

### Token format and lifetime

- Token is a SigV4-signed URL: `https://<endpoint>:<port>/?Action=connect&X-Amz-Algorithm=...`
- Token validity: 15 minutes from issuance.
- Token is region-scoped: a token generated in us-east-1 does not work
  in us-west-2.

## Engine-specific diagnostic queries

### PostgreSQL

```sql
-- Current connections vs limit
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;

-- Active connections by user
SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename;

-- Long-running queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE now() - query_start > interval '1 minute'
ORDER BY duration DESC;

-- Password expiry
SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname = '<user>';
```

### MySQL

```sql
-- Current connections vs limit
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Threads_connected';

-- Active connections by user
SELECT user, count(*) FROM information_schema.processlist GROUP BY user;

-- Long-running queries
SELECT id, user, host, time, state, info
FROM information_schema.processlist
WHERE time > 60 ORDER BY time DESC;

-- Password expiry / lock
SELECT user, host, password_expired, account_locked FROM mysql.user WHERE user = '<user>';
```

### SQL Server

```sql
-- Current connections
SELECT COUNT(*) FROM sys.dm_exec_connections;

-- Long-running sessions
SELECT session_id, status, total_elapsed_time, text
FROM sys.dm_exec_requests
CROSS APPLY sys.dm_exec_sql_text(sql_handle);
```

## Cross-VPC connectivity matrix

| Path | Required configuration |
| --- | --- |
| Same VPC, same AZ | Default VPC routing; no peering needed |
| Same VPC, cross-AZ | Default VPC routing; cross-AZ transfer fee applies |
| Peered VPC, same region | Active peering connection + routes both ways + SG allows (CIDR or peered-VPC SG) |
| Peered VPC, cross-region | Active cross-region peering + routes both ways + DNS resolution config |
| Transit Gateway | TGW attachment both VPCs + TGW route table propagation + routes both ways |
| On-prem to RDS (private) | VPN/Direct Connect + private hosted zone or VPC DNS forwarding |
| On-prem to RDS (public) | PubliclyAccessible=true + IGW + SG allows caller's public IP |

## AWS Health event categories that affect RDS connectivity

| Category | Likely impact |
| --- | --- |
| `AWS_RDS_MAINTENANCE_SCHEDULED` | Brief restart during maintenance window; connection refused |
| `AWS_RDS_HARDWARE_MAINTENANCE` | Underlying host replacement; Multi-AZ failover likely |
| `AWS_RDS_PERFORMANCE_DEGRADED` | Latency spike; engine-level issue |
| `AWS_RDS_STORAGE_FULL` | Capacity exhaustion; writes fail |
| `AWS_KMS_ISSUE` | Inaccessible KMS key; instance transitions to `inaccessible-encrypt-credentials` |
| `AWS_REGIONAL_EVENT` | Region-wide degradation; multiple services affected |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.

---

#### 6b: Stale DNS after failover (moved from SKILL.md)

After a Multi-AZ failover, the cluster endpoint updates to the new
writer, but DNS resolvers may serve the stale record for the TTL
window. Flush the resolver cache (`dig +trace`, restart the JVM, or
reduce the application's DNS TTL). If the application is on-prem
connecting over DX / VPN, the on-prem DNS resolver may cache longer.

