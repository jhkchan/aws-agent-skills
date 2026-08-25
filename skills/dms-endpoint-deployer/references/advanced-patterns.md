# DMS Endpoint Deployer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Configuration dependency graph (moved from SKILL.md)


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


## Expert heuristic: Secrets Manager for credential management (moved from SKILL.md)


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


## Step 10 — Recent features (moved from SKILL.md)


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

