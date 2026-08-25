# Engine Authentication & TLS Reference Guide

Supplementary reference for the RDS Connectivity Troubleshooter skill.
Loaded on-demand when a diagnostic needs IAM database auth token
lifecycle, TLS CA bundle rotation, engine-specific auth semantics, or
parameter-group / option-group conflict patterns.

## IAM database auth — token lifecycle

IAM database auth generates a SigV4-signed token used as the password.
The token is valid for 15 minutes. Connection pools that cache
connections longer than 15 minutes serve a stale token on the next
checkout and see `FATAL: password authentication failed`.

### Token generation

```text
Token = sigv4(
  method = GET,
  host = <instance-endpoint>,
  region = <region>,
  service = rds-db,
  credentials = <caller-iam-credentials>,
  query = {
    Action: connect,
    User: <database-user>,
    X-Amz-Expires: 900
  }
)
```

The token is sent as the password in the standard auth handshake. The
database engine validates it via the `rds_iam` (Postgres) /
`mysql_native_password` (MySQL) plugin that calls back to the AWS
auth service.

### Required IAM policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "rds-db:connect",
    "Resource": "arn:aws:rds-db:<region>:<account>:dbuser:<instance-or-cluster>/<db-user>"
  }]
}
```

Verify with `iam simulate-principal-policy`:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <app-role-arn> \
  --action-names rds-db:connect \
  --resource-arns arn:aws:rds-db:<region>:<account>:dbuser:<instance>/<user> \
  --output json
```

`implicitDeny` = the role policy lacks `rds-db:connect` on the
specified ARN. `explicitDeny` = a Deny statement (SCP, permissions
boundary, session policy) overrides the Allow.

### Database user creation

```sql
-- PostgreSQL
CREATE USER iam_app_role WITH PASSWORD DISABLE;
GRANT rds_iam TO iam_app_role;

-- MySQL
CREATE USER iam_app_role IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';
GRANT SELECT, INSERT, UPDATE, DELETE ON appdb.* TO iam_app_role;
```

A user created WITHOUT the IAM plugin cannot use IAM auth even with
the correct IAM policy — the engine falls back to password auth and
rejects the token.

### Common IAM-auth failure modes

| Pattern | ROOT_CAUSE | Fix |
|---|---|---|
| First N connections succeed, then auth fails; restart clears it | `AUTH_EXPIRED` — pool caches token > 15 min | Set pool `maxLifetime` < 14 min; regenerate token per checkout |
| All connections fail with `password authentication failed` | `AUTH_IAM_DB` — role lacks `rds-db:connect` OR DB user missing IAM plugin | Add the policy; create the user with the plugin |
| Works from one role but not another | `AUTH_IAM_DB` — resource ARN scope mismatch | Scope the policy to the correct instance + user |
| Token works locally but fails from EC2 / ECS | `AUTH_IAM_DB` — instance role differs from local | Verify the role assumed by the runtime |
| Works against writer but not reader | `AUTH_IAM_DB` — policy ARN lists only the writer | Add the reader instance to the policy resource list |

## TLS / SSL — CA bundle rotation

### CA certificate identifiers

| Identifier | Status | Notes |
|---|---|---|
| `rds-ca-2019` | Deprecated | Rotate to rds-ca-e2022/e2024 by Feb 2025 |
| `rds-ca-e2022` | Recommended | 2022 rotation; valid to ~2027 |
| `rds-ca-e2024` | Recommended (newer) | 2024 rotation for new instances |

Check the instance's current CA:

```bash
aws rds describe-db-instances --db-instance-identifier <id> \
  --output json | jq('.DBInstances[0].CACertificateIdentifier')
```

### Client trust store update

When the instance CA rotates from `rds-ca-2019` to `rds-ca-e2022` /
`e2024`, the client trust store MUST include the new CA. Otherwise the
TLS handshake fails with `unable to get local issuer certificate`
(Java), `certificate verify failed` (Python), or
`x509: certificate signed by unknown authority` (Go).

Download the new CA bundle from
https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html
and import it into the client trust store:

```bash
# Java keystore
keytool -importcert -alias rds-ca-e2024 \
  -keystore $JAVA_HOME/lib/security/cacerts \
  -file rds-combined-ca-bundle.pem -storepass changeit -noprompt

# OpenSSL (system trust store, Amazon Linux / AL2023)
sudo cp rds-combined-ca-bundle.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

### Engine TLS parameters

| Engine | Parameter | Effect |
|---|---|---|
| PostgreSQL | `rds.force_ssl = 1` | Reject non-TLS connections |
| MySQL | `require_secure_transport = 1` | Reject non-TLS connections |
| SQL Server | `rds.force_ssl = 1` + native engine TLS config | Enforce TLS |
| Oracle | Option group `SSL` option | Enforce TLS via option group |

When `force_ssl` / `require_secure_transport` is enabled and the
client connects without `sslmode=require` (Postgres) or
`requireSSL=true` (MySQL), the connection is rejected. The error
string contains `SSL connection required`.

### Connection string patterns

```bash
# PostgreSQL — verify-ca validates the CA but not the hostname
psql "host=<endpoint> port=5432 dbname=<db> user=<user> sslmode=verify-full sslrootcert=rds-ca-e2024.pem"

# MySQL — require TLS
mysql --host=<endpoint> --user=<user> --ssl-mode=REQUIRED --ssl-ca=rds-ca-e2024.pem

# JDBC (Java)
jdbc:postgresql://<endpoint>:5432/<db>?user=<user>&sslmode=verify-full&sslrootcert=/path/rds-ca-e2024.pem
```

## Parameter group override patterns

### Common parameters that break connectivity

| Parameter | Engine | Bad value | Effect |
|---|---|---|---|
| `max_connections` | MySQL / Postgres | Below the default for the instance class | `Too many connections` under load |
| `shared_buffers` | Postgres | Above 25% of instance memory | Instance fails to start after reboot |
| `rds.force_ssl` | Postgres | `1` on a non-TLS client | `SSL connection required` |
| `require_secure_transport` | MySQL | `1` on a non-TLS client | `SSL connection required` |
| `character_set_server` | MySQL | Changed post-creation | Collation errors on existing tables |
| `timezone` | Both | Set to a non-UTC zone | Application timestamp drift |

`max_connections` overrides on Aurora are IGNORED — Aurora derives the
limit from the instance class. Operators who "set max_connections to
8000" on an Aurora db.r6i.large (derived cap 6000) still see
`Too many connections` at 6000.

### Aurora derived max_connections formula

| Engine | Formula | Notes |
|---|---|---|
| Aurora PostgreSQL | `LEAST({DBInstanceClassMemory/9531392, 5000})` | Caps at 5000 by default |
| Aurora MySQL | `LEAST({DBInstanceClassMemory/9788476, 16000})` | Caps at 16000 by default |

Upsizing the instance class raises the derived limit automatically.
The fix for a derived-limit hit is instance-class upsize OR RDS
Proxy, NOT a parameter-group override.

## Option group conflicts

### Common conflict patterns

| Option | Engine | Conflict | Effect |
|---|---|---|---|
| `SSL` | Oracle | Required port in use | Option group apply fails |
| `SQLNET` | Oracle | Native auth + SSL both enabled | Auth handshake conflict |
| `NativeAuthentication` | SQL Server | Windows auth mode | `cannot connect` from SQL auth clients |
| `TDE` | SQL Server | Already enabled on a database | Option group apply fails |

When an option group apply fails, `describe-db-instances` shows
`DBInstanceStatus: incompatible-option-group` and
`describe-events` reports the specific option that failed. The fix is
to remove the conflicting option or resolve the prerequisite (free
port, disable native auth, etc.).

## Storage-full behaviour

When an RDS instance's allocated storage is exhausted:

1. `describe-db-instances` shows `StorageStatus: storage-full`.
2. The engine rejects all writes — INSERT / UPDATE / CREATE return
   `disk full` or `no space left on device`.
3. Connections may time out or drop entirely (some engines stop
   accepting new connections when the WAL / redo log cannot grow).
4. Reads may still succeed (read-only queries do not need disk).

The fix is storage auto-scaling:

```bash
aws rds modify-db-instance --db-instance-identifier <id> \
  --storage-auto-scaling --max-allocated-storage <N> \
  --apply-immediately
```

Storage auto-scaling expands the volume in the background (no
downtime). If the maximum threshold is already hit, raise
`--max-allocated-storage` further. Raising `max_connections`,
rebooting the instance, or upsizing the instance class does nothing —
the bottleneck is disk, not compute or memory.

## RDS Proxy connection patterns

RDS Proxy pools database connections and presents a proxy endpoint
that the application connects to instead of the direct instance /
cluster endpoint. Common misconfigurations:

| Pattern | ROOT_CAUSE | Fix |
|---|---|---|
| App connects to the instance endpoint, not the proxy endpoint | `CAPACITY_PROXY` | Update the connection string to the proxy endpoint |
| Proxy SG does not allow the client SG | `CAPACITY_PROXY` | Add an inbound rule to the proxy SG |
| Instance SG does not allow the proxy SG | `CAPACITY_PROXY` | Add an inbound rule to the instance SG for the proxy SG |
| Proxy's secrets ARN points at a deleted / rotated secret | `CAPACITY_PROXY` | Update the proxy's secret |
| Proxy target group points at a reader for writes | `CAPACITY_PROXY` | Set the target group role to `WRITER` or `WRITER/READER` |

Verify the proxy endpoint resolves and accepts connections:

```bash
aws rds describe-db-proxies --proxy-name <proxy> \
  --output json | jq('.DBProxies[0] | {Endpoint, Status,
    VpcSecurityGroupIds, RequireTLS}')

# From a host in the client subnet
nc -vz <proxy-endpoint> <port>
```

## DNS resolution patterns for Aurora endpoints

| Endpoint type | Routes to | TTL | Failover behaviour |
|---|---|---|---|
| Cluster endpoint | The current writer | ~1s | Updates within seconds of failover |
| Reader endpoint | Round-robins across readers | ~1s | Re-balances when readers are added / removed |
| Custom endpoint | A user-defined subset | ~1s | Static unless the membership is edited |
| Instance endpoint | A specific instance | ~5s | Does NOT follow failover; the old writer's endpoint still resolves but returns read-only |

After an Aurora failover:

1. The cluster endpoint updates to the new writer within seconds.
2. The old writer becomes a reader; its instance endpoint now returns
   `cannot execute INSERT in a read-only transaction` for writes.
3. JVM / application DNS caches may serve the stale record for longer
   than the 1s TTL — flush the cache (`dig +trace`, restart the JVM,
   or reduce the application's DNS TTL).
4. On-prem DNS resolvers connecting over DX / VPN may cache for
   minutes — coordinate with the network team to flush or lower the
   TTL.

---

### Step 8: RDS Proxy connectivity (moved from SKILL.md)

Symptom: `could not connect to proxy`, or the application hits the
instance directly despite a proxy being configured.

```bash
aws rds describe-db-proxies --proxy-name <proxy-name> --output json | \
  jq('.DBProxies[0] | {Status, EngineFamily,
    TargetRole, RequireTLS, VpcSubnetIds, VpcSecurityGroupIds}')

aws rds describe-db-proxy-target-groups --proxy-name <proxy-name> \
  --output json | jq('.TargetGroups[0]')
```

Common patterns:

| Pattern | ROOT_CAUSE |
|---|---|
| Proxy SG does not allow the client SG | `CAPACITY_PROXY` — fix the proxy SG |
| Proxy's target SG does not allow the proxy SG | `CAPACITY_PROXY` — fix the instance SG to allow the proxy |
| Proxy's secrets ARN points at a deleted / rotated secret | `CAPACITY_PROXY` — update the secret |
| Application connects to the instance endpoint, not the proxy endpoint | `CAPACITY_PROXY` — update the application's connection string |

#### 9a: Parameter group override (moved from SKILL.md)

If a recent parameter group change preceded the failure, a parameter
override may be the cause. Common culprits:

| Parameter | Effect |
|---|---|
| `max_connections` (MySQL/Postgres) | Set too low → `too many connections` |
| `rds.force_ssl` / `require_secure_transport` | Set to 1 → non-TLS clients rejected |
| `shared_buffers` (Postgres) | Set too high → instance fails to start after reboot |
| `character_set_server` (MySQL) | Changed → collation errors on existing tables |

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: PARAM_GROUP_OVERRIDE`.

#### 9b: Option group conflict (moved from SKILL.md)

If a recent option group change preceded the failure, an option may
conflict. Common patterns: SQL Server native auth, Oracle Advanced
Security, or a TLS option that requires a specific port. Confirm the
instance status is `incompatible-option-group` or check the events
for the option group apply failure. **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: OPTION_GROUP_CONFLICT`.

