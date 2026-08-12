# Rotation Strategy Reference Guide

Supplementary reference for the Secrets Manager Rotation
Troubleshooter skill. Loaded on-demand when a diagnostic needs the
differences between Alternating Users and Single User strategies, the
engine-specific template families, twin-secret replication semantics,
or the rollback / previous-credential behaviour.

## Strategy matrix

Secrets Manager rotation strategies are baked into the rotation
Lambda's code (the AWS-managed template family), not into the secret's
metadata. The choice of strategy affects: (1) what database privileges
the Master Secret's user needs, (2) whether the application experiences
a brief connection drop during rotation, and (3) whether the
`AWSPREVIOUS` staging label is meaningful for rollback.

| Strategy | Template family suffix | DB privileges required (Master Secret user) | Connection-drop risk | AWSPREVIOUS used | Atomicity |
|---|---|---|---|---|---|
| Single User | `*SingleUserRotation` | `ALTER USER` on the rotating user (MySQL: `SUPER` or `CREATE USER` + `UPDATE on mysql.user`; PostgreSQL: the user's own password OR a role with `CREATEROLE`) | Yes (brief; the application may see "password rejected" during the ALTER → reconnect window) | No (same user; no prior version to roll back to) | Atomic at the DB statement level |
| Alternating Users | `*MultiUserRotation` | `CREATE USER`, `GRANT`, `DROP USER`, `RENAME USER` (MySQL: `SUPER` + `CREATE USER`; PostgreSQL: `CREATEROLE` + role membership) | No (a clone user is rotated; the application's connection string swaps only after `testSecret` passes) | Yes (the prior user is demoted; rollback re-activates it) | Non-atomic across clone + swap + drop |
| Redshift Single | `SecretsManagerRedshiftRotationSingleUser` | `ALTER USER` on the rotating user | Yes | No | Atomic |
| Redshift Alternating | `SecretsManagerRedshiftRotationMultiUser` | `CREATE USER`, `GRANT`, transfer object ownership | No | Yes | Non-atomic |
| Generic | `SecretsManagerRotationGeneric` | Custom (the template's responsibility) | Custom | Custom | Custom |

### Single User — operational characteristics

The Single User strategy updates the existing database user's password
in place. The Lambda:

1. Reads the Master Secret to obtain a superuser credential.
2. Connects to the DB as the Master user.
3. Runs `ALTER USER '<rotating-user>' IDENTIFIED BY '<new-password>'`
   (MySQL), `ALTER ROLE "<rotating-user>" WITH PASSWORD '<new>'`
   (PostgreSQL), or the engine equivalent.
4. Tests the new credential.
5. Moves `AWSCURRENT` to the new version.

**Connection-drop risk:** applications holding an open connection
during step 3 are unaffected (existing connections stay open). New
connections attempted between step 3 and step 5 may use the cached
old password and fail. The window is typically < 1 second.

**AWSPREVIOUS is not meaningful:** the rotating user is the same; the
prior password is stored under `AWSPREVIOUS` but rolling back requires
re-running `ALTER USER` with the prior password. The standard rollback
path is to re-trigger rotation; the Lambda stages the prior password
as the new value.

**Use when:** the database engine does not support user cloning
(some DocumentDB configurations), or the application tolerates a
brief authentication blip, or the operational simplicity of one user
is preferred.

### Alternating Users — operational characteristics

The Alternating Users strategy clones the rotating user to a sibling
(e.g., `app_user_clone`), rotates the clone's password, then atomically
swaps the application's connection to the clone and disables the prior
user. The Lambda:

1. Reads the Master Secret to obtain a superuser credential.
2. Connects to the DB as the Master user.
3. Creates `<user>_clone` with the new password; copies all grants
   from `<user>` to `<user>_clone`.
4. Tests `<user>_clone` with the new password.
5. Renames `<user>` to `<user>_previous` and `<user>_clone` to
   `<user>` (MySQL `RENAME USER`; PostgreSQL uses a role-member swap).
6. Updates the secret value to point at the new `<user>` (same name).
7. Drops `<user>_previous` after a grace period.

**Connection-drop risk:** none. The swap is atomic; the application
sees the same `<user>` name throughout. Existing connections stay
open on `<user>_previous` until they reconnect.

**AWSPREVIOUS is meaningful:** the prior `<user>_previous` is the
rollback target. `testSecret` failure triggers a rollback to
`<user>_previous`.

**Use when:** the application cannot tolerate any authentication blip,
the database engine supports `CREATE USER` + `GRANT` + `RENAME USER`,
and the operational complexity of clone management is acceptable.

### Strategy conflict detection

The `STRATEGY_CONFLICT` layer applies when the rotation Lambda's
template family does not match the secret's expected strategy. Symptoms
include:

| Symptom | Conflict | Resolution |
|---|---|---|
| `ALTER USER failed; cannot modify own password` | Single User template authenticating as the rotating user (no Master) — should be Alternating | Re-deploy with Multi User template; or grant SUPER to the rotating user |
| `CREATE USER failed; already exists` (on the 2nd rotation) | Alternating template left a `<user>_clone` from a prior failed rotation; the cleanup step did not run | Manually drop the orphan clone; re-trigger rotation |
| `Rotating back to previous credential` on every attempt | `testSecret` fails; rollback path runs but `AWSPREVIOUS` does not exist (first rotation) | Investigate the `testSecret` failure first; rollback is the symptom |
| `permission denied for table mysql.user` | Single User template but the rotating user lacks `UPDATE on mysql.user` | Either grant `SUPER` to the rotating user (single-user) OR re-deploy with Multi User template (uses Master) |

## Engine-specific rotation templates

| Engine | Single User template | Multi User template | Notes |
|---|---|---|---|
| MySQL / Aurora-MySQL | `SecretsManagerRDSMySQLRotationSingleUser` | `SecretsManagerRDSMySQLRotationMultiUser` | `RENAME USER` supported; clone pattern works cleanly. |
| PostgreSQL / Aurora-PostgreSQL | `SecretsManagerRDSPostgreSQLRotationSingleUser` | `SecretsManagerRDSPostgreSQLRotationMultiUser` | No `RENAME ROLE`; the multi-user template uses a role-membership swap. |
| SQL Server | `SecretsManagerRDSSQLServerRotationSingleUser` | `SecretsManagerRDSSQLServerRotationMultiUser` | Uses `CREATE LOGIN` + `CREATE USER`; logins are server-scoped. |
| Oracle | `SecretsManagerRDSOracleRotationSingleUser` | `SecretsManagerRDSOracleRotationMultiUser` | Uses `ALTER USER` + `GRANT`; the multi-user template creates a schema-level clone. |
| Redshift | `SecretsManagerRedshiftRotationSingleUser` | `SecretsManagerRedshiftRotationMultiUser` | Redshift-specific; does NOT use the PostgreSQL template despite shared lineage. |
| Amazon DocumentDB (MongoDB-compatible) | `SecretsManagerMongoDBRotationSingleUser` | `SecretsManagerMongoDBRotationMultiUser` | Uses `createUser` / `updateUser` shell commands; DocumentDB-compatible. |
| Amazon ElastiCache (Redis AUTH) | `SecretsManagerRedisRotationSingleUser` | (none) | Single-user only; Redis does not support user cloning. |
| Generic / custom | `SecretsManagerRotationGeneric` | (none) | The user implements the four-step protocol; engine-agnostic. |

### Cross-engine template confusion — common pattern

Using a MySQL rotation Lambda on a PostgreSQL secret (or vice versa)
fails immediately in `setSecret` because the SQL syntax differs:

- MySQL: `ALTER USER '<user>'@'%' IDENTIFIED BY '<password>'`
- PostgreSQL: `ALTER ROLE "<user>" WITH PASSWORD '<password>'`
- SQL Server: `ALTER LOGIN <user> WITH PASSWORD = '<password>'`
- Oracle: `ALTER USER "<user>" IDENTIFIED BY "<password>"`
- Redshift: same syntax as PostgreSQL but uses a different system
  catalog; the PostgreSQL template fails on `pg_user` queries.

Verify the rotation Lambda's `Description` or `Environment.Variables`
identifies the correct engine before deep-diving into a `setSecret`
failure.

## Twin secrets and replication

Twin secrets are maintained via one of two mechanisms:

### Managed multi-region secrets (replicate-secret-to-regions)

```bash
aws secretsmanager replicate-secret-to-regions \
  --secret-id <primary-arn> \
  --add-replica-regions Region=<secondary-region> \
  --profile <primary-region-profile>
```

The replica's `PrimaryRegion` field is populated. The replica
auto-syncs the secret value within minutes of the primary's rotation.
Rotation runs ONLY in the primary region; the replica is read-only.

Failure symptoms:
- `describe-secret` in the secondary region shows
  `LastRotatedDate` > 1 hour behind the primary.
- `ReplicationStatus` shows `Status: FAILED`.
- The secondary region's secret value differs from the primary's.

Resolution:
- Re-run `replicate-secret-to-regions` with
  `--force-overwrite-replica-secret`.
- Investigate the KMS key policy in the secondary region (the replica
  is encrypted with the secondary region's CMK, which must grant the
  Secrets Manager service principal).

### Application-level twin secrets (independent rotation)

Two secrets in different regions with separate rotation configurations
(typically maintained by an application-level sync process or
CloudFormation stack-set).

Failure symptoms:
- Each region's `LastRotatedDate` is independent; one may be stale
  while the other is fresh.
- The application in the second region reads stale credentials and
  fails to connect.

Resolution:
- Verify the twin's `RotationEnabled` and `RotationLambdaARN` are
  correct in the second region.
- Trigger a manual rotation in the second region:
  `aws secretsmanager rotate-secret --secret-id <twin-arn> --region <secondary>`.

## Previous credential storage and rollback

The `AWSPREVIOUS` staging label is applied to the prior `AWSCURRENT`
version when `finishSecret` runs. The Lambda's `testSecret` step can
roll back to `AWSPREVIOUS` on failure.

Rollback scenarios:

| Scenario | Behaviour |
|---|---|
| First rotation on a new secret | No `AWSPREVIOUS` exists. `testSecret` failure produces `Rotating back to previous credential` log but the rollback itself fails because there is no previous. Investigate the `testSecret` failure first. |
| Second-and-after rotation | `AWSPREVIOUS` exists. Rollback re-applies the prior credential to the DB and the secret value. |
| Manual secret-value update (bypassing rotation) | The manual update creates a new `AWSCURRENT`; the prior moves to `AWSPREVIOUS`. The next rotation will attempt to roll back to the manual value if `testSecret` fails. |
| `AWSPENDING` stuck | A failed mid-protocol rotation leaves `AWSPENDING`. The next invocation attempts recovery from the failed step; `AWSPENDING` is cleared on success. |

## Rotation schedule cadence reference

| Schedule expression | Rotation frequency | Use case |
|---|---|---|
| `rate(1h)` | Hourly | High-churn environments; compliance-mandated short TTL |
| `rate(6h)` | Every 6 hours | Privileged-access secrets with strict rotation policy |
| `rate(1d)` | Daily | Standard compliance baseline (SOC 2, PCI DSS) |
| `rate(7d)` | Weekly | Application secrets with moderate sensitivity |
| `rate(30d)` | Monthly | Long-lived credentials where rotation is best-effort |
| `rate(90d)` | Quarterly | Low-sensitivity secrets; compliance minimum |

EventBridge schedule expressions have a 1-hour jitter. A `rate(1d)`
rule may fire at 03:17 one day and 04:02 the next. This is not a bug.
Verify the rule's `LastTriggered` time in `describe-rule` if the
operator reports rotation "firing late."

## Common rotation failure patterns by engine

### MySQL / Aurora-MySQL

| Error | Layer | Cause |
|---|---|---|
| `ERROR 1227 (42000): Access denied; you need (at least one of) the SUPER privilege(s)` | `SUPERUSER_INSUFFICIENT` | Single-User template; rotating user lacks SUPER. Fix: switch to Multi User template OR grant SUPER to the rotating user. |
| `ERROR 1396 (HY000): Operation ALTER USER failed for '<user>'@'%'` | `ROTATION_LAMBDA_DB_ENDPOINT` or `STRATEGY_CONFLICT` | The user does not exist on the target DB (wrong host) OR the host pattern is wrong (e.g., the secret has `'%'` but the user exists only at `'10.0.%'`). |
| `ERROR 1819 (HY000): Your password does not satisfy the current policy requirements` | `ROTATION_LAMBDA_DB_CREDENTIAL` | The Lambda generated a password that fails `validate_password` policy. Use a stronger password generator in the Lambda. |

### PostgreSQL / Aurora-PostgreSQL

| Error | Layer | Cause |
|---|---|---|
| `ERROR: must be superuser or have role "<rotating-user>" to alter role` | `SUPERUSER_INSUFFICIENT` | Master user lacks CREATEROLE or membership in the rotating role. Fix: `GRANT <rotating-user> TO <master-user>;` |
| `ERROR: role "<user>_clone" already exists` | `STRATEGY_CONFLICT` | A prior Alternating rotation left an orphan clone. Manually `DROP ROLE "<user>_clone";` and re-trigger. |
| `FATAL: password authentication failed for user "<user>"` (in `testSecret`) | `ROTATION_LAMBDA_DB_CREDENTIAL` | The `ALTER ROLE` succeeded but the password contains special characters that the connection string parser mishandles. URL-encode the password in the Lambda. |

### SQL Server

| Error | Layer | Cause |
|---|---|---|
| `ALTER LOGIN failed; user does not have permission` | `SUPERUSER_INSUFFICIENT` | Master user is not `sysadmin`. Fix: `ALTER SERVER ROLE sysadmin ADD MEMBER <master-user>;` |
| `Cannot alter the login '<user>', because it does not exist or you do not have permission.` | `ROTATION_LAMBDA_DB_ENDPOINT` | The login exists on a different SQL Server instance (wrong endpoint). |

### Redshift

| Error | Layer | Cause |
|---|---|---|
| `ERROR: relation "pg_user" does not exist` | `REDSHIFT_ROTATION_FUNCTION` | PostgreSQL rotation Lambda used on a Redshift cluster. Re-deploy with the Redshift-specific template. |
| `ERROR: permission denied for table pg_shadow` | `SUPERUSER_INSUFFICIENT` | Master user is not a Redshift superuser. Fix: `ALTER USER <master-user> CREATEUSER;` |

## Recent AWS features (2024-2026)

- **Rotation Lambda timeout default 30s on managed templates (2024):**
  New AWS-managed rotation templates set `Timeout=30` at deploy time.
  Older deployments and custom Lambdas may still have the 3s default.
- **Redshift multi-user rotation template GA (2024-2025):**
  `SecretsManagerRedshiftRotationMultiUser` reached GA after a long
  preview; previously Redshift rotation was single-user only.
- **EventBridge Scheduler for rotation (2025):** Secrets Manager can
  use EventBridge Scheduler (not just EventBridge rules) for finer-
  grained timing. Older setups still use rules; both are valid.
- **RotationFailed EventBridge event (2025):** Secrets Manager emits
  a `RotationFailed` event on repeated rotation failures. Subscribe
  via EventBridge for proactive alerting.
- **Cross-account rotation support (2024):** First-class support for
  cross-account rotation Lambda invocation. Still verify both the
  secret resource policy AND the Lambda resource-based policy for
  older setups.
