---
description: Provision an Amazon QLDB (Quantum Ledger Database) ledger with production-grade defaults (STANDARD permissions mode, deletion protection, KMS encryption, journal export to S3, streaming to Kinesis, cryptographic verification via digest + proof hash chain, PartiQL queries, Amazon Ion data format, indexed fields, table creation). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create qldb ledger"
  - "deploy qldb"
  - "qldb ledger"
  - "qldb permissions mode"
  - "qldb deletion protection"
  - "qldb journal export"
  - "qldb kinesis stream"
  - "qldb cryptographic verification"
  - "qldb digest"
  - "qldb proof"
  - "qldb hash chain"
  - "qldb partiql"
  - "qldb ion"
  - "immutable ledger database"
  - "qldb"
routes_to: qldb-ledger-deployer
---

# /aws:deploy-qldb-ledger

Activate the `qldb-ledger-deployer` skill and provision an Amazon QLDB
ledger with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Ledger architecture (immutable journal, append-only hash chain)
2. Permissions mode (STANDARD vs ALLOW_ALL)
3. Deletion protection (prevent catastrophic deletion)
4. KMS encryption (customer-managed key, immutable at creation)
5. Table creation and document model (Amazon Ion format)
6. PartiQL query language (SQL-compatible, semi-structured)
7. Indexed fields (single-field indexes, no compound indexes)
8. Journal export to S3 (compliance audit, regulatory snapshots)
9. Stream to Kinesis (real-time CDC, event-driven)
10. Cryptographic verification (digest + proof hash chain)
11. Revision hash chains (SHA-256 Merkle tree)
12. CloudWatch metrics (latency, conflicts, storage)

## When to use

- You need to create a QLDB ledger for immutable, auditable data.
- You need cryptographic proof that data has not been tampered with.
- You are setting up journal export for compliance audit.
- You need real-time CDC via Kinesis streaming.
- You need to configure STANDARD permissions mode with IAM policies.
- You are building a compliance system (SOX, HIPAA, GDPR, etc.).

## When NOT to use

- **Amazon DynamoDB** — use DynamoDB for general key-value/NoSQL workloads.
- **Amazon DocumentDB** — use DocumentDB for MongoDB-compatible workloads.
- **Amazon RDS** — use RDS for relational databases.
- **Amazon Timestream** — use Timestream for time-series data.
- **General-purpose data storage** — QLDB is purpose-built for immutable
  ledgers. If you do not need cryptographic verification, use DynamoDB.

## How to invoke

### Slash command

```
/aws:deploy-qldb-ledger
```

Then provide: ledger name, permissions mode (STANDARD), deletion
protection decision, KMS key (if customer-managed), table names, index
fields, export/streaming requirements, tags.

### Natural language

Any of these routes to the same skill:

- "create a QLDB ledger for compliance audit"
- "set up QLDB with cryptographic verification"
- "configure QLDB streaming to Kinesis for CDC"
- "export QLDB journal to S3"
- "provision an immutable ledger database"

### CLI routing

```bash
node cli/bin/cli.js route "create a qldb ledger"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create QLDB
ledgers. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-qldb-ledger

     Create a QLDB ledger named audit-ledger with STANDARD
     permissions mode, deletion protection, KMS encryption.
     Tables transactions, accounts. Indexes on transactionId
     and accountId. Set up S3 export and Kinesis streaming.

Skill:
  QLDB_LEDGER: audit-ledger
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Permissions mode: STANDARD
    [✓] Deletion protection: enabled
    [✓] Journal export to S3: configured
    [✓] Stream to Kinesis: configured
    [✓] Cryptographic verification: digest + proof workflow documented
    [✓] Revision hash chain: SHA-256 chained blocks
  VERIFICATION_COMMANDS:
    aws qldb describe-ledger --name audit-ledger --region us-east-1
    aws qldb list-journal-kinesis-streams-for-ledger --ledger-name audit-ledger --region us-east-1
    aws qldb get-digest --name audit-ledger --region us-east-1
```

## References

- Skill definition: `skills/qldb-ledger-deployer/SKILL.md`
- Verification and cryptography guide: `skills/qldb-ledger-deployer/references/verification-and-cryptography.md`
- Export and streaming guide: `skills/qldb-ledger-deployer/references/export-and-streaming.md`
- Eval suite: `skills/qldb-ledger-deployer/evals/evals.json`
