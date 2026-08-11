---
description: Provision an AWS DMS endpoint with production-grade defaults (source/target engine, connection attributes, Secrets Manager credentials, SSL mode with certificates, extra connection attributes for engine-specific tuning, KMS encryption, CDC prerequisites). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create dms endpoint"
  - "deploy dms endpoint"
  - "dms source endpoint"
  - "dms target endpoint"
  - "dms connection attributes"
  - "dms ssl"
  - "dms cdc"
  - "dms secrets manager"
  - "dms extra connection attributes"
  - "dms certificate"
  - "dms endpoint"
  - "database migration endpoint"
routes_to: dms-endpoint-deployer
---

# /aws:deploy-dms-endpoint

Activate the `dms-endpoint-deployer` skill and provision an AWS DMS
endpoint with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Source/target endpoint type selection
2. Engine selection (Oracle, MySQL, PostgreSQL, SQL Server, MongoDB, S3,
   Redshift, OpenSearch, Kinesis, Kafka, Neptune)
3. Connection attributes (host, port, database, credentials)
4. Secrets Manager integration for credential management
5. SSL mode selection (none, require, verify-ca, verify-full)
6. Certificate import and management
7. Extra connection attributes for engine-specific tuning
8. KMS encryption configuration
9. CDC prerequisites verification (engine-specific)
10. Replication instance compatibility check
11. Connection test

## When to use

- You need to create a DMS source or target endpoint.
- You are configuring CDC for a database migration.
- You need to manage DMS certificates and SSL modes.
- You want to use Secrets Manager for endpoint credentials.
- You need engine-specific extra connection attributes.
- You are setting up a migration to Redshift, OpenSearch, Kinesis,
  Kafka, or Neptune.

## When NOT to use

- **DMS replication task configuration** — use replication-task skills.
- **DMS replication instance provisioning** — use replication-instance
  skills.
- **AWS SCT (Schema Conversion Tool)** — use SCT-specific skills.
- **Auditing existing DMS endpoints** — use DMS audit skills.

## How to invoke

### Slash command

```
/aws:deploy-dms-endpoint
```

Then provide: endpoint type (source/target), engine name, server
hostname, port, database name, credentials (Secrets Manager secret ID
or inline), SSL mode, certificate identifier (if verify-ca/full), extra
connection attributes, KMS key ARN, replication instance ID, tags.

### Natural language

Any of these routes to the same skill:

- "create a DMS source endpoint for PostgreSQL with CDC"
- "configure a DMS target endpoint for S3 with Parquet format"
- "set up DMS with Secrets Manager for Oracle credentials"
- "configure verify-full SSL for my DMS endpoint"
- "create a MongoDB source endpoint with replica set CDC"

### CLI routing

```bash
node cli/bin/cli.js route "create a dms endpoint"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create DMS
endpoints. The output checklist feeds into verification pipelines and
downstream replication task skills.

## Example

```
You: /aws:deploy-dms-endpoint

     Create a DMS source endpoint for PostgreSQL at
     prod-db.cluster-abc123.us-east-1.rds.amazonaws.com
     port 5432, database analytics. Use Secrets Manager,
     verify-full SSL, pglogical CDC plugin. Account
     123456789012, us-east-1.

Skill:
  DMS_ENDPOINT: pg-source-prod (postgres, source)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Engine: postgres (port: 5432, database: analytics)
    [✓] Credentials: Secrets Manager
    [✓] SSL mode: verify-full
    [✓] Extra connection attributes: PluginName=pglogical
    [✓] CDC prerequisites: MET (wal_level=logical)
  VERIFICATION_COMMANDS:
    aws dms describe-endpoints --filters Name=endpoint-id,Values=pg-source-prod --region us-east-1
    aws dms test-connection --replication-instance-arn <arn> --endpoint-arn <arn> --region us-east-1
```

## References

- Skill definition: `skills/dms-endpoint-deployer/SKILL.md`
- CDC prerequisites guide: `skills/dms-endpoint-deployer/references/cdc-prerequisites.md`
- Connection tuning guide: `skills/dms-endpoint-deployer/references/connection-tuning.md`
- Eval suite: `skills/dms-endpoint-deployer/evals/evals.json`
