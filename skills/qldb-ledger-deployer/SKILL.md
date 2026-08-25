---
name: qldb-ledger-deployer
description: 'Provisions Amazon QLDB (Quantum Ledger Database) ledgers with production defaults: ledger creation (create-ledger), permissions mode (STANDARD vs ALLOW_ALL), deletion protection, KMS encryption, PartiQL query language, Amazon Ion data format, journal export to S3, stream to Kinesis Data Streams, cryptographic verification (digest + proof), revision hash chains, indexed fields, table creation, document model, and CloudWatch metrics. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a QLDB ledger, configuring permissions mode, enabling deletion protection, setting up journal export, streaming to Kinesis, verifying data integrity with digests and proofs, creating tables and indexes, or writing PartiQL queries. Triggers: create qldb ledger, qldb permissions mode, qldb deletion protection, qldb journal export, qldb stream to kinesis, qldb cryptographic verification, qldb digest, qldb proof, qldb partiql, qldb ion data format, qldb hash chain, qldb index, qldb table creation.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with qldb access. Works with Terraform aws_qldb_ledger / aws_qldb_stream / aws_qldb_s3_export_task resources and the AWS SDK for PartiQL (qldb-session, qldb APIs).'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, qldb, ledger, cloudops, deploy, databases, provisioning, immutable, cryptographic, partiql, ion, hash-chain
  dependencies: aws-orchestrator
  keywords: aws, qldb, quantum ledger database, immutable ledger, cloudops, deploy, provisioning, partiql, amazon ion, hash chain, cryptographic verification, journal export, kinesis stream, deletion protection, digest, proof
  when_to_use: Invoke when the user wants to create an Amazon QLDB ledger, configure permissions mode (STANDARD vs ALLOW_ALL), enable deletion protection, set up journal export to S3, stream journal data to Kinesis for real-time CDC, verify data integrity using cryptographic digests and proofs, create tables and indexes, or write PartiQL queries against Ion-format documents. Do NOT invoke for Amazon DynamoDB (use DynamoDB skills), Amazon DocumentDB (use DocumentDB skills), Amazon Timestream (use Timestream skills), or Amazon RDS (use RDS skills).
---

# QLDB Ledger Deployer

An AWS CloudOps agent skill that provisions Amazon QLDB (Quantum Ledger
Database) ledgers with correct defaults. The skill walks the operator
through ledger creation, permissions mode (STANDARD vs ALLOW_ALL),
deletion protection, KMS encryption, table and index creation, journal
export to S3 for compliance audit, stream to Kinesis for real-time CDC,
and cryptographic verification via digest and proof hash chains,
captures integrity and compliance decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create QLDB ledger, QLDB permissions mode, QLDB deletion protection,
QLDB journal export, QLDB Kinesis stream, QLDB cryptographic
verification, QLDB digest, QLDB proof, QLDB PartiQL, QLDB Ion data
format, QLDB hash chain, QLDB index, QLDB table creation.

## STRICT output contract

When this skill is invoked with a QLDB-provisioning request (create a
ledger, configure permissions mode, set up journal export, configure
Kinesis streaming, verify data integrity, create tables and indexes, or
a partial configuration), the agent MUST respond with the
`LEDGER:` / `VERDICT:` / `CHECKLIST:` / `PARTIQL:` / `JOURNAL_EXPORT:` /
`STREAM:` / `VERIFICATION_COMMANDS:` block defined in "Output format"
using the literal all-caps labels. Do NOT preface the block with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### FORBIDDEN output patterns

- **NEVER preface the block with prose** — `LEDGER:` is the FIRST
  line, always. No greetings, no "I'll set up…", no disclaimers.
- **NEVER use ALLOW_ALL for a production ledger** — ALWAYS use
  STANDARD permissions mode. ALLOW_ALL grants full CRUD to any
  principal with `qldb:SendCommand`.
- **NEVER omit deletion protection in a READY_TO_DEPLOY plan** —
  a production ledger without deletion protection is a data-loss
  risk.
- **NEVER emit placeholder KMS key IDs** — use the full key ARN
  (e.g., `arn:aws:kms:us-east-1:123456789012:key/abc123`) or
  state `aws-owned` explicitly.
- **NEVER omit the PARTIQL block** — concrete `CREATE TABLE`,
  `CREATE INDEX`, and `INSERT` statements must appear with real
  table and field names.
- **NEVER claim READY_TO_DEPLOY with empty JOURNAL_EXPORT or
  STREAM sections** — if not configured, write `none` with a
  reason; do not silently omit.
- **NEVER swap verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`, not "ready", "done", "ok".
- **NEVER emit compound indexes** — QLDB supports only
  single-field indexes; one `CREATE INDEX` per field.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Ledger architecture (immutable journal) | Core model |
| Step 2 — Permissions mode (STANDARD vs ALLOW_ALL) | Security |
| Step 3 — Deletion protection | Safety |
| Step 4 — KMS encryption | Security |
| Step 5 — Table creation and document model (Ion) | Data model |
| Step 6 — PartiQL query language | Querying |
| Step 7 — Indexed fields | Performance |
| Step 8 — Journal export to S3 (compliance audit) | Compliance |
| Step 9 — Stream to Kinesis (real-time CDC) | Integration |
| Step 10 — Cryptographic verification (digest + proof) | Integrity |
| Step 11 — Revision hash chains | Cryptography |
| Step 12 — CloudWatch metrics | Observability |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/verification-and-cryptography.md | Digest/proof + hash chain detail |
| references/export-and-streaming.md | S3 export + Kinesis stream detail |

## Mindset

**One-line takeaway:** Amazon QLDB is a purpose-built immutable ledger
database where every document revision is cryptographically chained via
SHA-256 hashes. Data cannot be silently modified — any tampering breaks
the hash chain. Verification is done by requesting a digest (a hash of
the entire journal at a point in time) and proving a specific revision
belongs to that digest.

Three misconceptions dominate QLDB misdesign at provisioning time:

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#common-misconceptions-from-mindset).
> Three QLDB misconceptions: not a generic NoSQL DB, ALLOW_ALL is unsafe, export/stream must be planned at creation.

## Configuration dependency graph (novel heuristic)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-sequencing-notes).
> How to sequence provisioning using the dependency graph.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Ledger (create-ledger) | permissions mode, deletion protection, KMS key | permissions mode and deletion protection can be modified after creation; KMS key cannot be changed without recreating the ledger | tables, journal, exports, streams |
| Permissions mode | ledger exists | STANDARD enforces IAM-based table/field controls; ALLOW_ALL grants full access | access control |
| Deletion protection | ledger exists | when enabled, ledger CANNOT be deleted until disabled | safety |
| KMS key | key exists (if customer-managed) | KMS key is immutable after ledger creation | encryption at rest |
| Table creation | ledger is active | QLDB does not enforce a schema; documents in the same table can have different fields | data storage |
| Indexes | table exists | creating an index on a large table takes time; queries without indexes are full scans | query performance |
| Journal export to S3 | ledger exists; S3 bucket with write access | export is asynchronous; can take hours for large journals | compliance audit, data lake |
| Stream to Kinesis | ledger exists; Kinesis stream exists; IAM role with qldb:SendCommand + kinesis:PutRecord | stream is continuous; covers a configurable time range | real-time CDC |
| Digest | ledger exists | digest is a point-in-time hash of the entire journal | cryptographic verification baseline |
| Proof | digest exists; document revision known | proof verifies that a specific revision belongs to the digest's hash chain | tamper detection |

**The permissions-mode and deletion-protection rows are the ones a
baseline model misses.** ALLOW_ALL in a production ledger is a security
hole. Missing deletion protection risks catastrophic data loss.

## Expert heuristic: immutable journal hash chain verification

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-immutable-journal-hash-chain-verification).
> Digest + proof verification workflow and expert rules.

## Expert heuristic: stream for real-time CDC vs export for compliance audit

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-stream-for-real-time-cdc-vs-export-for-compliance-audit).
> Export to S3 vs stream to Kinesis decision guide.

## Expert heuristic: STANDARD permissions mode enforcement

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-standard-permissions-mode-enforcement).
> ALLOW_ALL vs STANDARD comparison and enforcement rule.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Permissions mode decision (STANDARD vs ALLOW_ALL) | Controls access model | Assess security requirements |
| Deletion protection decision | Prevents accidental deletion | `aws qldb describe-ledger` |
| KMS key (if customer-managed) | Encryption at rest | `aws kms describe-key --key-id <alias>` |
| S3 bucket (if journal export planned) | Export destination | `aws s3 ls` |
| Kinesis stream (if streaming planned) | CDC destination | `aws kinesis describe-stream` |
| IAM role for export/streaming | Service-to-service access | `aws iam get-role` |
| Table and index design | Data model planning | Assess query patterns |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Ledger architecture (immutable journal)

QLDB uses an immutable journal architecture. Every transaction appends
journal entries that are cryptographically chained.

| Component | Role | API |
|---|---|---|
| Ledger | Top-level container, permissions, encryption, deletion protection | `create-ledger` |
| Journal | Append-only, cryptographically hashed chain of blocks | automatic |
| Block | Group of transactions, each with a hash linking to the previous block | `get-block` |
| Table | Collection of documents (schemaless) | PartiQL `CREATE TABLE` |
| Document | Amazon Ion-format data record with a unique document ID | PartiQL `INSERT` |
| Revision | A specific version of a document (each update creates a new revision) | `get-revision` |
| Index | B-tree index on a table field for query performance | PartiQL `CREATE INDEX` |

**The journal is the source of truth.** Tables and indexes are derived
views. Every document revision is permanently recorded in the journal.

## Step 2 — Permissions mode (STANDARD vs ALLOW_ALL)

```bash
# Create a ledger with STANDARD permissions mode (recommended)
aws qldb create-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --region us-east-1

# Modify permissions mode (after creation)
aws qldb update-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --region us-east-1
```

> Moved to [references/worked-examples.md](references/worked-examples.md#step-2-standard-mode-iam-policy-example).
> IAM policy allowing SendCommand plus PartiQLInsert/Select at table scope.

## Step 3 — Deletion protection

```bash
# Create with deletion protection enabled
aws qldb create-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --region us-east-1

# Disable deletion protection (required before deleting a ledger)
aws qldb update-ledger \
  --name audit-ledger \
  --no-deletion-protection \
  --region us-east-1
```

**Expert rule:** deletion protection prevents deletion even with
administrator privileges. Always enable it for production ledgers.

## Step 4 — KMS encryption

```bash
aws qldb create-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --kms-key arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --region us-east-1
```

**Critical:** the KMS key is immutable after ledger creation. To change
the encryption key, you must create a new ledger and migrate data.

## Step 5 — Table creation and document model (Ion)

QLDB stores data in Amazon Ion format — a rich, self-describing data
format that is a superset of JSON. Tables are schemaless.

> Moved to [references/worked-examples.md](references/worked-examples.md#step-5-table-creation-and-document-model-ion-sql-examples).
> CREATE TABLE, Ion INSERT, SELECT, and UPDATE (revision) statements.

## Step 6 — PartiQL query language

QLDB uses PartiQL — a SQL-compatible query language that handles
semi-structured data.

> Moved to [references/worked-examples.md](references/worked-examples.md#step-6-partiql-query-examples).
> SELECT, projection, nested Ion paths, JOIN, and history() queries.

**History queries** are unique to QLDB — they return ALL revisions of a
document, showing the complete mutation history. This is the audit trail.

## Step 7 — Indexed fields

QLDB indexes are critical for query performance. Without an index, every
query is a full table scan.

```sql
-- Create indexes on single fields (no compound indexes in QLDB)
CREATE INDEX ON transactions (transactionId);
CREATE INDEX ON transactions (fromAccount);
CREATE INDEX ON accounts (accountId);
```

**Indexing rules:**
- Create indexes BEFORE inserting large amounts of data
- Indexes are on a SINGLE field (no compound indexes in QLDB)
- The `documentId` field is automatically indexed
- Queries on unindexed fields are full scans

## Step 8 — Journal export to S3 (compliance audit)

Journal export writes the entire journal (or a time range) to S3 in Ion
format. This is for compliance audit, regulatory snapshots, and data
lake ingestion.

> Moved to [references/export-and-streaming.md](references/export-and-streaming.md#step-8-journal-export-to-s3-commands).
> IAM role setup, put-role-policy, and export-journal-to-s3 commands plus export output notes.

## Step 9 — Stream to Kinesis (real-time CDC)

QLDB streams journal data to Kinesis Data Streams for real-time CDC.

> Moved to [references/export-and-streaming.md](references/export-and-streaming.md#step-9-stream-to-kinesis-commands).
> Kinesis stream creation, QLDBStreamRole IAM setup, and stream-journal-to-kinesis command.

**Expert rule:** use streaming for real-time CDC and export for
compliance audit. They serve different purposes and can run in parallel.

## Step 10 — Cryptographic verification (digest + proof)

Cryptographic verification proves that a document has not been tampered
with since a given point in time. This is QLDB's killer feature.

> Moved to [references/verification-and-cryptography.md](references/verification-and-cryptography.md#step-10-cryptographic-verification-digest-and-proof-commands).
> get-digest, get-revision with digest tip, Python proof verification, expert rules.

## Step 11 — Revision hash chains

> Moved to [references/verification-and-cryptography.md](references/verification-and-cryptography.md#step-11-revision-hash-chains).
> How block hashes chain and why tampering breaks the chain.

## Step 12 — CloudWatch metrics

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-12-cloudwatch-metrics).
> Metric table with alert thresholds (latency, journal storage, IOs, OccConflictExceptions).

## NEVER do these things

1. **NEVER use ALLOW_ALL permissions mode for production.** ALLOW_ALL
   grants full CRUD to anyone with `qldb:SendCommand`. ALWAYS use
   STANDARD.

2. **NEVER deploy a production ledger without deletion protection.**
   Without it, a single errant `delete-ledger` destroys the entire
   journal irreversibly.

3. **NEVER skip index creation on fields used in WHERE clauses.** QLDB
   has no query optimizer. Queries on unindexed fields are full scans.

4. **NEVER assume the KMS key can be changed after creation.** The KMS
   key is immutable. Changing encryption requires recreating the ledger.

5. **NEVER treat QLDB as a general-purpose NoSQL database.** QLDB is
   purpose-built for immutable, cryptographically verified data. If you
   do not need the audit trail, use DynamoDB.

6. **NEVER wait until an audit is requested to set up journal export.**
   Set up export and streaming pipelines at ledger creation.

7. **NEVER store digests in the same ledger they verify.** Store them
   externally (S3 with Object Lock).

8. **NEVER use compound indexes.** QLDB supports only single-field
   indexes. For multi-field queries, create separate indexes.

9. **NEVER ignore OccConflictExceptions.** High conflict rates indicate
   concurrent writes to the same document.

10. **NEVER delete a ledger without disabling deletion protection
    first.**

## Output format — MANDATORY literal labels

When invoked with a QLDB provisioning request, your ENTIRE
response MUST be the block below. The labels are **case-sensitive
all-caps keywords** — write them EXACTLY as shown. Do NOT write a
preamble. Start with `LEDGER:` and stop after
`VERIFICATION_COMMANDS:`.

```text
LEDGER: <ledger-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Permissions mode: STANDARD | ALLOW_ALL
  [✓|✗] Deletion protection: enabled | disabled
  [✓|✗] KMS encryption: <customer-managed|aws-owned> (<key-arn>)
  [✓|✗] Tables: <list of table names>
  [✓|✗] Indexes: <field list per table>
  [✓|✗] Journal export: <configured|none> (bucket: <name>, role: <arn>)
  [✓|✗] Kinesis stream: <configured|none> (stream: <name>, role: <arn>)
  [✓|✗] Cryptographic verification: digest + proof workflow documented
  [✓|✗] CloudWatch alerts: <metrics list>
  [✓|✗] Tags: <key=value list>
PARTIQL:
  CREATE TABLE <table-name>;
  CREATE INDEX ON <table-name> (<field>);
  INSERT INTO <table-name> { ... };
JOURNAL_EXPORT:
  Role: <IAM role ARN>
  Bucket: s3://<bucket>/<prefix>
  Time range: <start> to <end>
STREAM:
  Kinesis stream: <stream-name>
  Role: <IAM role ARN>
  Time range: <start> to <end>
  Aggregation: enabled | disabled
VERIFICATION_COMMANDS:
  aws qldb describe-ledger --name <ledger-name> --region <region>
  aws qldb list-journal-kinesis-streams-for-ledger --ledger-name <ledger-name> --region <region>
  aws qldb get-digest --name <ledger-name> --region <region>
```

**Status marker semantics:**
- `[✓]` — requirement met.
- `[✗]` — requirement missing; cite the gap.

**PREREQUISITES_MISSING verdict:** if any checklist item fails,
output `VERDICT: PREREQUISITES_MISSING` with each gap marked `[✗]`
and a reason. Do NOT also emit `READY_TO_DEPLOY`.

### Worked example — STANDARD-mode audit ledger with KMS + Kinesis stream

```text
LEDGER: audit-ledger
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Permissions mode: STANDARD
  [✓] Deletion protection: enabled
  [✓] KMS encryption: customer-managed (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Tables: transactions, accounts, audit_log
  [✓] Indexes: transactions(transactionId, fromAccount), accounts(accountId), audit_log(eventType)
  [✓] Journal export: configured (bucket: s3://qldb-audit-export/audit-ledger/2026-08/, role: arn:aws:iam::123456789012:role/QLDBExportRole)
  [✓] Kinesis stream: configured (stream: qldb-audit-stream, role: arn:aws:iam::123456789012:role/QLDBStreamRole)
  [✓] Cryptographic verification: digest + proof workflow documented
  [✓] CloudWatch alerts: CommandExecutionLatency >1000ms, OccConflictExceptions >5%, JournalStorage trending up
  [✓] Tags: Environment=production, Application=audit, Compliance=SOX, Owner=finance-platform
PARTIQL:
  CREATE TABLE transactions;
  CREATE TABLE accounts;
  CREATE TABLE audit_log;
  CREATE INDEX ON transactions (transactionId);
  CREATE INDEX ON transactions (fromAccount);
  CREATE INDEX ON accounts (accountId);
  CREATE INDEX ON audit_log (eventType);
  INSERT INTO transactions {
    transactionId: 'txn-001',
    amount: 1500.00,
    currency: 'USD',
    fromAccount: 'acc-aaa',
    toAccount: 'acc-bbb',
    timestamp: `2026-08-05T12:00:00Z`,
    metadata: { source: 'mobile-app', notes: 'Transfer for invoice #12345' }
  };
JOURNAL_EXPORT:
  Role: arn:aws:iam::123456789012:role/QLDBExportRole
  Bucket: s3://qldb-audit-export/audit-ledger/2026-08/
  Time range: 2026-08-01T00:00:00Z to 2026-08-31T23:59:59Z
STREAM:
  Kinesis stream: qldb-audit-stream
  Role: arn:aws:iam::123456789012:role/QLDBStreamRole
  Time range: 2026-08-05T00:00:00Z to 2026-12-31T23:59:59Z
  Aggregation: enabled
VERIFICATION_COMMANDS:
  aws qldb describe-ledger --name audit-ledger --region us-east-1
  aws qldb list-journal-kinesis-streams-for-ledger --ledger-name audit-ledger --region us-east-1
  aws qldb get-digest --name audit-ledger --region us-east-1
```

## Error handling

> Moved to [references/error-handling.md](references/error-handling.md#error-handling).
> Symptom-by-symptom fixes: permissions mode, deletion, slow queries, export, stream, Occ conflicts.
## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — expert-heuristic deep dives, misconceptions, dependency-graph notes
- [worked-examples](references/worked-examples.md) — IAM policy, Ion/PartiQL SQL examples
- [diagnostic-commands](references/diagnostic-commands.md) — CloudWatch metrics and alert thresholds
- [error-handling](references/error-handling.md) — symptom-by-symptom troubleshooting
- [export-and-streaming](references/export-and-streaming.md) — S3 export and Kinesis stream detail and commands (existing)
- [verification-and-cryptography](references/verification-and-cryptography.md) — digest/proof and hash-chain detail and commands (existing)

## Domain

AWS CloudOps / Amazon QLDB Ledger Provisioning & Cryptographically
Verified Immutable Database Management.

## AWS documentation

- **QLDB Developer Guide** — https://docs.aws.amazon.com/qldb/latest/developerguide/what-is.html
- **Create a ledger** — https://docs.aws.amazon.com/qldb/latest/developerguide/ledger-create.html
- **Permissions modes** — https://docs.aws.amazon.com/qldb/latest/developerguide/ledger-management.permissions.html
- **PartiQL queries** — https://docs.aws.amazon.com/qldb/latest/developerguide/data-model.partiql.html
- **Amazon Ion** — https://docs.aws.amazon.com/qldb/latest/developerguide/ion.html
- **Journal export to S3** — https://docs.aws.amazon.com/qldb/latest/developerguide/export-journal.html
- **Stream to Kinesis** — https://docs.aws.amazon.com/qldb/latest/developerguide/streams.html
- **Cryptographic verification** — https://docs.aws.amazon.com/qldb/latest/developerguide/verification.html
- **Digests and proofs** — https://docs.aws.amazon.com/qldb/latest/developerguide/verification.digests.html
- **Indexes** — https://docs.aws.amazon.com/qldb/latest/developerguide/working-data.indexes.html
