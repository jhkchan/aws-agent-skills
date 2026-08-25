---
name: dms-endpoint-deployer
description: 'Provisions AWS DMS endpoints with production defaults: source endpoint (Oracle, MySQL, PostgreSQL, SQL Server, MongoDB, S3), target endpoint (same set plus Redshift, OpenSearch, Kinesis, Kafka, Neptune), connection attributes (port, database name, credentials via Secrets Manager), SSL mode (require, verify-ca, verify-full), extra connection attributes for engine-specific tuning, KMS encryption, certificate authority for TLS, replication instance requirements, engine version compatibility, and source-specific CDC prerequisites (PostgreSQL wal_level=logical, Oracle supplemental logging). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a DMS endpoint, configuring connection attributes, setting up CDC, managing DMS certificates, or tuning extra connection attributes. Triggers: create dms endpoint, dms source endpoint, dms target endpoint, dms ssl, dms cdc, dms secrets manager, dms certificate.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with dms access (and secretsmanager:GetSecretValue if using Secrets Manager for credentials). Works with Terraform aws_dms_endpoint resources and CloudFormation AWS::DMS::Endpoint templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Migration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, dms, endpoint, migration, cloudops, deploy, provisioning, cdc, ssl, secrets-manager, source-endpoint, target-endpoint
  dependencies: aws-orchestrator
  keywords: aws, dms, database migration service, endpoint, source endpoint, target endpoint, cdc, change data capture, ssl, secrets manager, cloudops, deploy, provisioning, oracle, mysql, postgresql, sql server, mongodb, redshift, opensearch, kinesis, kafka
  when_to_use: Invoke when the user wants to create a DMS endpoint (source or target), configure connection attributes, set up CDC replication prerequisites, manage DMS certificates and SSL, use Secrets Manager for endpoint credentials, or tune extra connection attributes for engine-specific behavior. Do NOT invoke for DMS replication task configuration (use dms-replication-task skills), DMS replication instance provisioning (use replication-instance skills), or SCT (Schema Conversion Tool) operations.
---

# DMS Endpoint Deployer

An AWS CloudOps agent skill that provisions AWS DMS endpoints with
correct defaults. The skill walks the operator through source and
target endpoint selection, connection attribute configuration
(database name, port, username/password via Secrets Manager), SSL
mode selection, extra connection attributes for engine-specific
tuning, KMS encryption, certificate authority for TLS, engine
version compatibility, and source-specific CDC prerequisites — then
captures all decisions and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create DMS endpoint, DMS source endpoint, DMS target endpoint, DMS
connection attributes, DMS SSL, DMS CDC, DMS Secrets Manager, DMS
extra connection attributes, DMS certificate.

## STRICT output contract

When this skill is invoked with a DMS-endpoint-provisioning request
(create a source or target endpoint, configure connection attributes,
set up CDC prerequisites, manage certificates, or tune extra connection
attributes), the agent MUST respond with the READY_TO_DEPLOY checklist
defined in the "Output format" section using the literal all-caps labels
`DMS_ENDPOINT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[x]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Source endpoint types | Source DB selection |
| Step 2 — Target endpoint types | Target store selection |
| Step 3 — Connection attributes | Host, port, database, credentials |
| Step 4 — Secrets Manager integration | Credential management |
| Step 5 — SSL mode and certificates | TLS configuration |
| Step 6 — Extra connection attributes | Engine-specific tuning |
| Step 7 — KMS encryption | Encryption at rest |
| Step 8 — CDC prerequisites | Change data capture setup |
| Step 9 — Replication instance compatibility | Instance requirements |
| Step 10 — Recent features | Latest DMS capabilities |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/cdc-prerequisites.md | CDC detail per engine |
| references/connection-tuning.md | Extra connection attributes detail |

## Mindset

**One-line takeaway:** A DMS endpoint defines the connection
parameters for a source or target data store. Source endpoints read
data (and optionally CDC changes). Target endpoints receive data.
The endpoint's engine type determines which connection attributes
and extra connection attributes are valid. CDC requires source-
specific prerequisites (e.g., PostgreSQL `wal_level=logical`, Oracle
supplemental logging). Credentials should use Secrets Manager. SSL
modes enforce TLS at varying verification levels.

Three misconceptions dominate DMS endpoint misdesign at provisioning
time:

- **"Create the endpoint and migration works."** It does not. The
  endpoint is the connection definition, but CDC requires source-
  specific prerequisites that are OUTSIDE DMS. PostgreSQL needs
  `wal_level=logical` and a replication slot. Oracle needs supplemental
  logging enabled. SQL Server needs SQL Server Agent running for CDC.
  Without these, the endpoint connects but CDC fails silently or with
  cryptic errors.

- **"SSL mode 'require' is sufficient for security."** SSL mode
  `require` encrypts the connection but does NOT verify the server
  certificate. A man-in-the-middle can intercept. For production,
  use `verify-ca` (verifies the certificate authority) or `verify-
  full` (verifies the CA AND the server hostname). These require a
  certificate to be uploaded to DMS via `import-certificate`.

- **"Extra connection attributes are optional tuning."** They are
  often REQUIRED for correct behavior. PostgreSQL CDC needs
  `PluginName=pglogical`. MongoDB needs `NestingLevel=ONE` or
  `NONE`. S3 target needs `DataFormat=parquet`. Oracle needs
  `AdditionalArchivedLogDestId`. Skipping extra connection attributes
  leads to default behavior that may not match the migration
  requirements.

## Configuration dependency graph (novel heuristic)

DMS endpoint configurations are NOT independent. The engine type
determines valid connection attributes. The SSL mode determines
whether a certificate is needed. CDC mode determines source-specific
prerequisites. The replication instance engine version must be
compatible with the endpoint engine. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Endpoint (basic) | Replication instance exists; engine type specified; host/port/database set | credentials must be valid at connection test time; endpoint type (source/target) is immutable | replication task |
| Secrets Manager | Secret exists in Secrets Manager; DMS role has `secretsmanager:GetSecretValue` | secret ARN specified instead of inline password; secret rotation does NOT automatically update the DMS endpoint | secure credential management |
| SSL mode | Certificate imported to DMS (for verify-ca/verify-full); CA bundle available | `require` encrypts without verification; `verify-ca` and `verify-full` need imported certificate | TLS-encrypted connection |
| Extra connection attributes | Engine type identified; specific attributes valid for that engine | invalid attributes are silently ignored by some engines; syntax errors cause test-connection failure | engine-specific behavior tuning |
| KMS key | KMS key exists; DMS service has `kms:Decrypt` and `kms:GenerateDataKey` | default DMS-managed key if not specified; customer-managed key enables cross-account and CloudTrail | encryption at rest |
| CDC (PostgreSQL) | `wal_level=logical` on source; `max_replication_slots` > 0; replication slot created; `PluginName` set | if `wal_level` is not logical, CDC tasks fail with a slot-creation error that does not mention wal_level | logical replication CDC |
| CDC (Oracle) | Supplemental logging enabled (`ALTER DATABASE ADD SUPPLEMENTAL LOG DATA`); ARCHIVELOG mode on; DMS user has DBA privileges | without supplemental logging, CDC misses UPDATE/DELETE operations | Oracle CDC |
| CDC (SQL Server) | SQL Server Agent running; CDC enabled on database and tables; DMS user in db_owner role | without SQL Server Agent, CDC capture job never starts | SQL Server CDC |
| Replication instance | Instance exists; engine version compatible with endpoint engines | instance must be in the same VPC/subnet group as source (for private sources); AllocatedStorage limits throughput | endpoint connectivity test |
| Certificate | CA cert imported via `import-certificate`; certificate ARN referenced in endpoint | certificate expiration causes silent SSL failures; DMS does NOT auto-rotate certificates | verify-ca / verify-full SSL modes |

**The CDC-prerequisites row is the one a baseline model misses.**
Creating the endpoint succeeds (the connection test passes), but CDC
tasks fail later because the source database is not configured for
logical replication. The procedure below forces an explicit CDC
prerequisite check per engine type.

**Cross-dependency gotchas:**
- The replication instance engine version must be compatible with the
  endpoint engine. Check the DMS compatibility matrix before creating
  endpoints.
- Secrets Manager rotation does NOT automatically update the DMS
  endpoint. If the source database password is rotated, the DMS
  endpoint must be re-tested or re-created with the new secret.
- SSL `verify-ca` and `verify-full` require an imported certificate.
  Without it, the endpoint test fails.
- Extra connection attributes have engine-specific syntax. Attributes
  valid for PostgreSQL are NOT valid for Oracle and vice versa.
- KMS encryption uses the DMS service role, not the endpoint's
  credentials. Ensure the DMS role has KMS permissions.

## Expert heuristic: source-specific CDC prerequisites

A baseline model says "create the endpoint and enable CDC." The correct
heuristic recognizes that CDC prerequisites are OUTSIDE DMS — they are
on the source database itself.

```text
CDC prerequisites by engine:
  PostgreSQL:
    ├── wal_level=logical (check: SHOW wal_level)
    ├── max_replication_slots >= 1 (check: SHOW max_replication_slots)
    ├── Endpoint extra attr: PluginName=pglogical (or test_decoding)
    └── Replication slot auto-created by DMS

  Oracle:
    ├── ARCHIVELOG mode enabled (check: ARCHIVE LOG LIST)
    ├── Supplemental logging: ALTER DATABASE ADD SUPPLEMENTAL LOG DATA
    ├── Force logging (optional): ALTER DATABASE FORCE LOGGING
    └── DMS user privileges: SELECT ANY TRANSACTION, EXECUTE on DBMS_LOGMNR

  MySQL:
    ├── Binary logging enabled (log_bin=ON)
    ├── binlog_format=ROW
    ├── binlog_row_image=FULL
    └── DMS user: REPLICATION SLAVE, REPLICATION CLIENT, SELECT

  SQL Server:
    ├── SQL Server Agent running
    ├── CDC enabled on database (sys.sp_cdc_enable_db)
    ├── CDC enabled on tables (sys.sp_cdc_enable_table)
    └── DMS user in db_owner role (or sysadmin)

  MongoDB:
    ├── Replica set (standalone NOT supported for CDC)
    └── DMS user with clusterMonitor and readWrite roles
```

**Key implication:** the #1 cause of DMS CDC failures is missing
source-database prerequisites. The endpoint connection test passes
(basic connectivity works), but CDC tasks fail with errors like
"could not create replication slot" (PostgreSQL) or "supplemental
logging not enabled" (Oracle). Always verify source prerequisites
BEFORE creating the endpoint.

## Expert heuristic: Secrets Manager for credential management

A baseline model puts inline passwords in the endpoint. The correct
heuristic uses Secrets Manager for all credentials.

```text
Secrets Manager integration flow:
  1. Create a secret in Secrets Manager with the DB credentials
     {
       "username": "dms_user",
       "password": "<password>",
       "engine": "postgres",
       "host": "prod-db.cluster-abc123.us-east-1.rds.amazonaws.com",
       "port": 5432,
       "dbInstanceIdentifier": "prod-db"
     }
  2. Grant the DMS service role secretsmanager:GetSecretValue on the secret
  3. Create the DMS endpoint with --secrets-manager-access-role-arn
     and --secrets-manager-secret-id (instead of inline credentials)
  4. DMS retrieves credentials at connection time
```

**Key implication:** using Secrets Manager eliminates hardcoded
passwords in CloudFormation/Terraform state files. Secret rotation
updates the source DB password without touching DMS config — but the
DMS endpoint must be re-tested after rotation to pick up the new
password.

## Expert heuristic: extra-connection-attributes for engine tuning

Extra connection attributes (`--extra-connection-attributes` or
`ExtraConnectionAttributes` in CloudFormation) are the primary
mechanism for engine-specific tuning. They use a semicolon-delimited
key=value syntax.

```text
Common extra connection attributes by engine:
  PostgreSQL source (CDC):
    PluginName=pglogical;slotName=dms_slot;secretsManagerSecretId=prod-db-secret

  Oracle source (CDC):
    AdditionalArchivedLogDestId=1;EnableHomogenousTablespace=true;ExtraArchivedLogDestIds=2

  MySQL source (CDC):
    eventsPollInterval=5;initstmt=SET FOREIGN_KEY_CHECKS=0

  MongoDB source:
    NestingLevel=ONE;ExtractDocId=true;DocsToInvestigate=50

  S3 target:
    DataFormat=parquet;EncodingType=rle-dictionary;CompressionType=snappy

  Redshift target:
    AcceptAnyDate=true;AfterConnectScript=SET search_path TO dms;MaxFileSize=100000

  Kinesis target:
    MessageFormat=json;ServiceAccessRoleArn=arn:aws:iam::...
```

**Key implication:** skipping extra connection attributes results in
default behavior that often does NOT match migration requirements.
Always specify engine-specific attributes explicitly.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Replication instance exists | Endpoints connect through the instance | `aws dms describe-replication-instances` |
| Source/target database reachable | Endpoint test requires connectivity | Verify VPC/subnet/security group for private DBs |
| Source CDC prerequisites met (if CDC) | CDC tasks fail without source DB config | PostgreSQL: `SHOW wal_level`; Oracle: check supplemental logging |
| Secrets Manager secret (if using SM) | DMS needs GetSecretValue permission | `aws secretsmanager describe-secret --secret-id <id>` |
| Certificate imported (if verify-ca/full) | SSL verification needs the CA cert | `aws dms describe-certificates` |
| KMS key ARN (if customer-managed) | DMS needs KMS permissions | `aws kms describe-key --key-id <id>` |
| DMS service role has required permissions | Endpoint creation + connection test | Verify `dms-vpc-role` and `dms-cloudwatch-logs-role` exist |
| Engine version compatibility | Instance and endpoints must be compatible | Check DMS compatibility matrix |

## Step 1 — Source endpoint types

DMS supports multiple source endpoint engines. Each has specific
connection attributes.

| Engine | EndpointType | CDC support | Key attributes |
|---|---|---|---|
| Oracle | source | Yes (LogMiner / Binary Reader) | Port 1521, SID/ServiceName, AdditionalArchivedLogDestId |
| MySQL | source | Yes (binary log) | Port 3306, binlog_format=ROW |
| PostgreSQL | source | Yes (logical replication) | Port 5432, PluginName=pglogical |
| SQL Server | source | Yes (SQL Server CDC) | Port 1433, SQL Server Agent required |
| MongoDB | source | Yes (oplog/change streams) | Port 27017, replica set required |
| Amazon S3 | source | No (full load only) | BucketName, CsvColumnName, DataFormat |

**Create PostgreSQL source endpoint:**

```bash
aws dms create-endpoint \
  --endpoint-identifier "pg-source-prod" \
  --endpoint-type source \
  --engine-name postgres \
  --username dms_user \
  --password '<password>' \
  --server-name prod-db.cluster-abc123.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --database-name analytics \
  --ssl-mode require \
  --extra-connection-attributes "PluginName=pglogical" \
  --kms-key-id "arn:aws:kms:us-east-1:123456789012:key/abc123" \
  --region us-east-1
```

## Step 2 — Target endpoint types

DMS supports the same source engines as targets, plus additional
analytical targets.

| Engine | EndpointType | Full load + CDC | Key attributes |
|---|---|---|---|
| Redshift | target | Yes | Port 5439, AcceptAnyDate, MaxFileSize |
| OpenSearch | target | Yes | EndpointUri, FullLoadErrorPercentage |
| Kinesis | target | Yes (CDC to stream) | StreamArn, MessageFormat=json |
| Kafka | target | Yes (CDC to topic) | Broker, Topic, MessageFormat |
| Neptune | target | Yes (graph) | S3BucketName, ServiceAccessRoleArn |
| S3 | target | Yes | DataFormat=parquet, CompressionType |

**Create Redshift target endpoint:**

```bash
aws dms create-endpoint \
  --endpoint-identifier "redshift-target" \
  --endpoint-type target \
  --engine-name redshift \
  --username dms_loader \
  --password '<password>' \
  --server-name analytics-cluster.abc123.us-east-1.redshift.amazonaws.com \
  --port 5439 \
  --database-name warehouse \
  --ssl-mode require \
  --extra-connection-attributes "AcceptAnyDate=true;MaxFileSize=100000" \
  --region us-east-1
```

## Step 3 — Connection attributes

Each endpoint engine type requires specific connection attributes.

| Attribute | Required for | Description |
|---|---|---|
| ServerName | All JDBC endpoints | Hostname or IP of the database server |
| Port | All JDBC endpoints | Database port (engine-specific default) |
| DatabaseName | Most endpoints | Target database/schema name |
| Username | Most endpoints | Database user with read (source) or write (target) access |
| Password | Most endpoints | User password (prefer Secrets Manager) |
| S3BucketName | S3 source/target | S3 bucket for data files |
| BucketFolder | S3 source/target | Folder path within the bucket |
| ServiceAccessRoleArn | S3/Kinesis/Kafka/Neptune | IAM role for service-level access |

## Step 4 — Secrets Manager integration

Use Secrets Manager instead of inline credentials for security.

**Create endpoint with Secrets Manager:**

```bash
aws dms create-endpoint \
  --endpoint-identifier "pg-source-prod" \
  --endpoint-type source \
  --engine-name postgres \
  --secrets-manager-access-role-arn "arn:aws:iam::123456789012:role/dms-vpc-role" \
  --secrets-manager-secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:dms-pg-prod-abc123" \
  --database-name analytics \
  --ssl-mode require \
  --extra-connection-attributes "PluginName=pglogical" \
  --region us-east-1
```

The secret must contain `username`, `password`, `engine`, `host`,
`port`, and `dbInstanceIdentifier` in its JSON payload. The DMS
service role must have `secretsmanager:GetSecretValue` on the secret.

**Important:** Secrets Manager rotation does NOT automatically update
the DMS endpoint. After rotation, re-test the endpoint connection.

## Step 5 — SSL mode and certificates

| SSL mode | Encryption | Certificate verification | Hostname verification | Requires imported cert |
|---|---|---|---|---|
| none | No | No | No | No |
| require | Yes | No | No | No |
| verify-ca | Yes | Yes (CA) | No | Yes |
| verify-full | Yes | Yes (CA) | Yes (hostname) | Yes |

**Import a certificate:**

```bash
aws dms import-certificate \
  --certificate-identifier "prod-ca-cert" \
  --certificate-pkcs12 "fileb://prod-ca.p12" \
  --certificate-password '<cert_password>' \
  --region us-east-1
```

**Create endpoint with verify-full SSL:**

```bash
aws dms create-endpoint \
  --endpoint-identifier "pg-source-secure" \
  --endpoint-type source \
  --engine-name postgres \
  --username dms_user \
  --password '<password>' \
  --server-name prod-db.cluster-abc123.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --database-name analytics \
  --ssl-mode verify-full \
  --certificate-arn "arn:aws:dms:us-east-1:123456789012:cert:prod-ca-cert" \
  --region us-east-1
```

## Step 6 — Extra connection attributes

Engine-specific tuning via semicolon-delimited key=value pairs.

**PostgreSQL source (CDC):**

```bash
--extra-connection-attributes "PluginName=pglogical;slotName=dms_replication_slot;secretsManagerSecretId=prod-db-secret"
```

**Oracle source (CDC with Binary Reader):**

```bash
--extra-connection-attributes "useLogminerReader=N;AdditionalArchivedLogDestId=1;EnableHomogenousTablespace=true"
```

**S3 target (Parquet format):**

```bash
--extra-connection-attributes "DataFormat=parquet;EncodingType=rle-dictionary;CompressionType=snappy;AddColumnName=true"
```

## Step 7 — KMS encryption

DMS encrypts endpoint connection data at rest using KMS.

```bash
aws dms create-endpoint \
  --endpoint-identifier "pg-source-prod" \
  --endpoint-type source \
  --engine-name postgres \
  --username dms_user \
  --password '<password>' \
  --server-name prod-db.cluster-abc123.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --database-name analytics \
  --kms-key-id "arn:aws:kms:us-east-1:123456789012:key/abc123" \
  --region us-east-1
```

If not specified, DMS uses the default `aws/dms` managed key. A
customer-managed key enables cross-account access and CloudTrail
audit logging.

## Step 8 — CDC prerequisites

CDC (Change Data Capture) requires source-database-level configuration
that is OUTSIDE DMS. See the Expert heuristic section and the
`references/cdc-prerequisites.md` reference for per-engine details.

| Engine | Key prerequisite | Verification command |
|---|---|---|
| PostgreSQL | `wal_level=logical`, `max_replication_slots >= 1` | `SHOW wal_level; SHOW max_replication_slots;` |
| Oracle | ARCHIVELOG mode, supplemental logging | `ARCHIVE LOG LIST; SELECT supplemental_log_data_min FROM v$database;` |
| MySQL | `log_bin=ON`, `binlog_format=ROW`, `binlog_row_image=FULL` | `SHOW VARIABLES LIKE 'log_bin'; SHOW VARIABLES LIKE 'binlog_format';` |
| SQL Server | SQL Server Agent running, CDC enabled | `SELECT name, is_cdc_enabled FROM sys.databases;` |
| MongoDB | Replica set (not standalone) | `rs.status()` |

## Step 9 — Replication instance compatibility

The replication instance engine version must be compatible with the
endpoint engine versions.

```bash
# Check available engine versions
aws dms describe-engine-versions \
  --region us-east-1

# Check replication instance
aws dms describe-replication-instances \
  --filters Name=replication-instance-id,Values=rep-instance-prod \
  --region us-east-1
```

**Compatibility rules:**
- PostgreSQL 12+ requires DMS engine version 3.4.6+.
- Oracle CDC with Binary Reader requires DMS engine version 3.4.4+.
- MongoDB change streams requires DMS engine version 3.4.4+ and
  MongoDB 4.0+.
- S3 target with Parquet requires DMS engine version 3.4.0+.

## Step 10 — Recent features

**Recent AWS DMS features (2023-2026):**

- **DMS Serverless (2023-2024):** DMS Serverless auto-scales capacity
  for replication tasks without pre-provisioning replication instances.
  Endpoints remain the same; the replication task config changes.

- **PostgreSQL 16 support (2024-2025):** DMS engine version 3.5.x
  added PostgreSQL 16 source and target support, including improved
  logical replication slot handling.

- **OpenSearch target improvements (2023-2024):** Enhanced OpenSearch
  target endpoint with better bulk indexing and error handling via
  `FullLoadErrorPercentage` and `ErrorRetryDuration`.

- **Kafka MSK integration (2023-2024):** Improved Kafka target endpoint
  with SASL/SCRAM authentication support and schema registry
  integration.

- **Secrets Manager auto-retry (2024-2025):** DMS endpoints using
  Secrets Manager now auto-retry credential retrieval on transient
  failures, reducing connection test failures during secret rotation.

- **Engine version 3.5.x (2024-2025):** New engine version with
  improved parallelism for large-table full load, reduced CDC latency
  for PostgreSQL, and bug fixes for Oracle Binary Reader.

## NEVER do these things

1. **NEVER skip CDC prerequisites on the source database.** Creating
   the endpoint succeeds, but CDC tasks fail. PostgreSQL needs
   `wal_level=logical`. Oracle needs supplemental logging. SQL Server
   needs SQL Server Agent running. Always verify source prerequisites.

2. **NEVER use inline passwords in production.** Use Secrets Manager
   for all endpoint credentials. Inline passwords are visible in
   CloudFormation/Terraform state and API call logs.

3. **NEVER use SSL mode `require` for production.** `require` encrypts
   without certificate verification, allowing man-in-the-middle. Use
   `verify-ca` or `verify-full` with an imported certificate.

4. **NEVER skip extra connection attributes for engine-specific
   behavior.** PostgreSQL CDC needs `PluginName=pglogical`. S3 target
   needs `DataFormat=parquet`. Oracle Binary Reader needs
   `useLogminerReader=N`. Defaults often do not match requirements.

5. **NEVER assume Secrets Manager rotation auto-updates the DMS
   endpoint.** After rotation, the DMS endpoint must be re-tested
   to pick up the new password. Monitor for connection failures after
   rotation.

6. **NEVER create an endpoint without a replication instance.** The
   endpoint connection test requires a replication instance to route
   through. Verify the instance exists and is in the correct VPC.

7. **NEVER use a standalone MongoDB instance for CDC.** CDC requires
   a replica set. Standalone MongoDB only supports full load (no CDC).

8. **NEVER forget to check engine version compatibility.** The
   replication instance engine version must support the endpoint
   engine. PostgreSQL 16 requires DMS 3.5.x. Check the compatibility
   matrix.

9. **NEVER use `none` SSL mode for any endpoint with sensitive data.**
   All traffic is unencrypted. Use at minimum `require` (and ideally
   `verify-full`) for any production workload.

10. **NEVER assume extra connection attribute syntax errors are
    caught.** Some engines silently ignore invalid attributes. Others
    fail the connection test. Always test-connection after creating
    the endpoint.

11. **NEVER reuse the same replication slot name across DMS tasks.**
    PostgreSQL replication slots are exclusive. Two tasks using the
    same slot will conflict. Use unique slot names per task.

12. **NEVER skip the test-connection step.** Always run
    `test-connection` after creating the endpoint and before creating
    the replication task. This catches credential, network, and SSL
    issues early.

## Output format

```text
DMS_ENDPOINT: <endpoint-identifier> (<engine-name>, <source|target>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Endpoint type: <source|target>
  [✓|✗] Engine: <engine-name> (port: <port>, database: <database-name>)
  [✓|✗] Server: <server-name>
  [✓|✗] Credentials: Secrets Manager (<secret-id>) | Inline (not recommended for production)
  [✓|✗] SSL mode: <none|require|verify-ca|verify-full> (certificate: <cert-arn> | N/A)
  [✓|✗] Extra connection attributes: <list of key=value pairs> | None
  [✓|✗] KMS key: <kms-key-arn> | Default DMS managed key
  [✓|✗] CDC prerequisites: MET (<engine-specific items>) | N/A (full load only)
  [✓|✗] Replication instance: <instance-id> (engine version: <version>, status: available)
  [✓|✗] Engine version compatibility: PASS
  [✓|✗] Connection test: PASS
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws dms describe-endpoints --filters Name=endpoint-id,Values=<endpoint-identifier> --region <region>
  aws dms test-connection --replication-instance-arn <instance-arn> --endpoint-arn <endpoint-arn> --region <region>
```

### Worked example — PostgreSQL source endpoint with CDC

```text
DMS_ENDPOINT: pg-source-prod (postgres, source)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Endpoint type: source
  [✓] Engine: postgres (port: 5432, database: analytics)
  [✓] Server: prod-db.cluster-abc123.us-east-1.rds.amazonaws.com
  [✓] Credentials: Secrets Manager (arn:aws:secretsmanager:us-east-1:123456789012:secret:dms-pg-prod-abc123)
  [✓] SSL mode: verify-full (certificate: arn:aws:dms:us-east-1:123456789012:cert:prod-ca-cert)
  [✓] Extra connection attributes: PluginName=pglogical;slotName=dms_replication_slot
  [✓] KMS key: arn:aws:kms:us-east-1:123456789012:key/abc123
  [✓] CDC prerequisites: MET (wal_level=logical, max_replication_slots=5)
  [✓] Replication instance: rep-instance-prod (engine version: 3.5.2, status: available)
  [✓] Engine version compatibility: PASS (PostgreSQL 16 supported by DMS 3.5.x)
  [✓] Connection test: PASS
  [✓] Tags: Environment=production, MigrationType=cdc
VERIFICATION_COMMANDS:
  aws dms describe-endpoints --filters Name=endpoint-id,Values=pg-source-prod --region us-east-1
  aws dms test-connection --replication-instance-arn arn:aws:dms:us-east-1:123456789012:rep:rep-instance-prod --endpoint-arn arn:aws:dms:us-east-1:123456789012:endpoint:pg-source-prod --region us-east-1
```

## Error handling

### Connection test fails with timeout
- Verify the replication instance is in the same VPC and subnet group
  as the source/target database. Check security group rules allow
  inbound from the replication instance on the database port.

### CDC task fails with "could not create replication slot"
- PostgreSQL: verify `wal_level=logical` and `max_replication_slots >
  0`. Check for conflicting slot names. Verify the DMS user has
  `REPLICATION` privilege.

### CDC task misses UPDATE/DELETE operations (Oracle)
- Supplemental logging is not enabled. Run `ALTER DATABASE ADD
  SUPPLEMENTAL LOG DATA` and `ALTER TABLE ... ADD SUPPLEMENTAL LOG
  DATA (ALL) COLUMNS` for all replicated tables.

### SSL handshake fails
- For `verify-ca` / `verify-full`, verify the certificate is imported
  and not expired. Check that the certificate ARN in the endpoint
  matches the imported certificate.

### Secrets Manager credential retrieval fails
- Verify the DMS service role has `secretsmanager:GetSecretValue` on
  the secret. Check the secret's JSON payload includes `username` and
  `password` fields. If the secret was recently rotated, re-test the
  endpoint connection.

## Domain

AWS CloudOps / AWS Database Migration Service (DMS) Endpoint
Provisioning & Configuration.

## AWS documentation

- **DMS User Guide** — https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html
- **Creating endpoints** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Endpoints.html
- **Source engines** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.html
- **Target engines** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.html
- **Extra connection attributes** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Intro.ConnectionAttribute.html
- **SSL for DMS** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.html
- **Secrets Manager with DMS** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.html#security-iam-secretsmanager
- **CDC prerequisites** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.QReplication.html
- **DMS API** — https://docs.aws.amazon.com/dms/latest/APIReference/Welcome.html
