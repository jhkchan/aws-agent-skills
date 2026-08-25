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

- **"QLDB is just another NoSQL database."** It is NOT. QLDB is a
  cryptographically verified ledger. Every transaction produces journal
  entries that are chained by SHA-256 hashes. You can mathematically
  prove that a document has not been tampered with by requesting a
  digest and verifying a proof. If you do not need this guarantee, use
  DynamoDB instead.

- **"ALLOW_ALL permissions mode is fine for simplicity."** It is NOT.
  ALLOW_ALL grants full CRUD to any IAM principal with access to QLDB.
  For a ledger whose entire purpose is immutability and auditability,
  ALWAYS use STANDARD permissions mode for production, which enforces
  table-level and field-level IAM controls.

- **"I can export or stream the journal later when I need it."** You
  can, but the export/stream should be planned at provisioning time.
  Journal export to S3 is for compliance audit (point-in-time snapshots).
  Streaming to Kinesis is for real-time CDC (continuous). Set up the
  export pipeline and/or stream at creation time.

## Configuration dependency graph (novel heuristic)

QLDB configurations are NOT independent. The ledger must exist before
tables. Tables must exist before indexes. The permissions mode and
deletion protection are set at creation. Use this graph to sequence
provisioning.

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

A baseline model says "QLDB stores data immutably." The correct
heuristic recognizes that immutability is only valuable if you can
PROVE it — and the proof mechanism (digest + proof) must be integrated
into your verification workflow.

```text
QLDB cryptographic verification flow:
  1. DIGEST: a Merkle-like hash of the entire journal at time T
     digest = qldb.get_digest(ledger_name)
  2. REVISION: the current state of a document
     revision = qldb.get_revision(ledger_name, document_id, block_address)
  3. PROOF: the hash chain from the revision to the digest
     proof = qldb.get_revision(ledger_name, document_id, block_address, digest)
  4. VERIFY: hash the revision, walk the proof chain, compare to digest:
     computed = sha256(revision)
     for node in proof: computed = sha256(computed + node)
     assert computed == digest

  Expert rule:
    Request digests periodically (e.g., daily).
    Store digests in a separate, secure store (S3 with Object Lock).
    Use proofs to verify any document on-demand.
```

## Expert heuristic: stream for real-time CDC vs export for compliance audit

```text
Journal export to S3:
  Purpose: compliance audit, point-in-time snapshot, data lake ingestion
  Trigger: on-demand or scheduled (e.g., nightly)
  Latency: hours (for large journals)

Stream to Kinesis Data Streams:
  Purpose: real-time change data capture (CDC)
  Trigger: continuous (started with a start time)
  Latency: near real-time (seconds)

Expert rule:
  Export to S3 = compliance audit (batch, periodic, full journal)
  Stream to Kinesis = real-time CDC (continuous, incremental, event-driven)
  Use BOTH for a complete data pipeline.
```

## Expert heuristic: STANDARD permissions mode enforcement

```text
ALLOW_ALL (NOT recommended):
  Every IAM principal with qldb:SendCommand has FULL CRUD on ALL tables.
  No table-level or field-level control. Risk: any compromised credential
  can modify or delete ledger data.

STANDARD (recommended for ALL production ledgers):
  IAM policies control access at the TABLE and FIELD level.
  Example policy allows INSERT on 'transactions' but not DELETE.

Expert rule:
  ALWAYS use STANDARD permissions mode.
  Define IAM policies per table and per operation BEFORE switching.
```

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

**STANDARD mode IAM policy example:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "qldb:SendCommand",
      "Resource": "arn:aws:qldb:us-east-1:123456789012:ledger/audit-ledger"
    },
    {
      "Effect": "Allow",
      "Action": ["qldb:PartiQLInsert", "qldb:PartiQLSelect"],
      "Resource": "arn:aws:qldb:us-east-1:123456789012:ledger/audit-ledger/table/*"
    }
  ]
}
```

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

```sql
-- Create tables
CREATE TABLE transactions;
CREATE TABLE accounts;
CREATE TABLE audit_log;

-- Insert a document (Ion format)
INSERT INTO transactions
{
    transactionId: 'txn-001',
    amount: 1500.00,
    currency: 'USD',
    fromAccount: 'acc-aaa',
    toAccount: 'acc-bbb',
    timestamp: `2026-08-05T12:00:00Z`,
    metadata: { source: 'mobile-app', notes: 'Transfer for invoice #12345' }
};

-- Query documents
SELECT * FROM transactions WHERE transactionId = 'txn-001';

-- Update a document (creates a new revision, old revision preserved)
UPDATE transactions SET status = 'confirmed' WHERE transactionId = 'txn-001';
```

## Step 6 — PartiQL query language

QLDB uses PartiQL — a SQL-compatible query language that handles
semi-structured data.

```sql
-- Basic SELECT
SELECT * FROM transactions WHERE amount > 1000;
-- Project specific fields
SELECT transactionId, amount, status FROM transactions;
-- Query nested data (Ion)
SELECT t.transactionId, t.metadata.source
FROM transactions t WHERE t.metadata.source = 'mobile-app';
-- JOIN tables
SELECT t.transactionId, a.accountName
FROM transactions t, accounts a WHERE t.fromAccount = a.accountId;
-- History query (see all revisions of a document)
SELECT * FROM history(transactions) AS h WHERE h.data.transactionId = 'txn-001';
```

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

```bash
# Create IAM role that QLDB assumes to write to S3
aws iam create-role \
  --role-name QLDBExportRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"qldb.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy \
  --role-name QLDBExportRole \
  --policy-name QLDBExportS3Policy \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:PutObject","s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::qldb-audit-export","arn:aws:s3:::qldb-audit-export/*"]}]}'

# Export the journal to S3
aws qldb export-journal-to-s3 \
  --name audit-ledger \
  --export-name audit-export-2026-08 \
  --role-arn arn:aws:iam::123456789012:role/QLDBExportRole \
  --output-s3-prefix s3://qldb-audit-export/audit-ledger/2026-08/ \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-31T23:59:59Z \
  --region us-east-1
```

**Export output:** S3 objects in Ion-formatted journal blocks. Each
block includes the block hash, transaction metadata, and document
revisions.

## Step 9 — Stream to Kinesis (real-time CDC)

QLDB streams journal data to Kinesis Data Streams for real-time CDC.

```bash
# Prerequisite: create the Kinesis stream
aws kinesis create-stream --stream-name qldb-audit-stream --shard-count 1 --region us-east-1
aws kinesis wait stream-active --stream-name qldb-audit-stream --region us-east-1

# Create IAM role for QLDB to write to Kinesis
aws iam create-role \
  --role-name QLDBStreamRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"qldb.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy \
  --role-name QLDBStreamRole \
  --policy-name QLDBStreamKinesisPolicy \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["kinesis:PutRecord","kinesis:PutRecords"],"Resource":"arn:aws:kinesis:us-east-1:123456789012:stream/qldb-audit-stream"}]}'

# Start streaming journal data to Kinesis
aws qldb stream-journal-to-kinesis \
  --ledger-name audit-ledger \
  --role-arn arn:aws:iam::123456789012:role/QLDBStreamRole \
  --inclusive-start-time 2026-08-05T00:00:00Z \
  --exclusive-end-time 2026-12-31T23:59:59Z \
  --kinesis-configuration StreamName=qldb-audit-stream,AggregationEnabled=true \
  --stream-name audit-ledger-cdc-stream \
  --region us-east-1
```

**Expert rule:** use streaming for real-time CDC and export for
compliance audit. They serve different purposes and can run in parallel.

## Step 10 — Cryptographic verification (digest + proof)

Cryptographic verification proves that a document has not been tampered
with since a given point in time. This is QLDB's killer feature.

```bash
# Request a digest (point-in-time hash of the entire journal)
aws qldb get-digest --name audit-ledger --region us-east-1

# Get a document revision with proof against the digest
aws qldb get-revision \
  --name audit-ledger \
  --block-address '{"IonText":"{strandId:\"abc\",sequenceNo:42}"}' \
  --document-id "abc-document-id" \
  --digest-tip-address '{"IonText":"{strandId:\"abc\",sequenceNo:100}"}' \
  --region us-east-1
```

**Verify the proof (Python):**

```python
import hashlib

def verify_proof(revision_hash, proof_hashes, digest):
    computed = revision_hash
    for sibling in proof_hashes:
        computed = hashlib.sha256(computed + sibling).digest()
    return computed == digest
# True = document is VERIFIED (untampered)
# False = tampering detected (should never happen in QLDB)
```

**Expert rule:** request digests periodically (daily or weekly). Store
them externally (S3 with Object Lock). Use proofs to verify any document
on-demand.

## Step 11 — Revision hash chains

Every revision in QLDB is part of a cryptographic hash chain:

```text
Block N:   Block Hash = SHA-256(Block N contents + Block N-1 hash)
Block N+1: Block Hash = SHA-256(Block N+1 contents + Block N hash)

The chain: each block's hash includes the previous block's hash.
Modifying any revision changes its hash → changes its block hash →
breaks every subsequent block hash → detected by digest verification.
```

## Step 12 — CloudWatch metrics

| Metric | What it measures | Alert threshold |
|---|---|---|
| CommandExecutionLatency | PartiQL execution time | > 1000ms sustained |
| JournalStorage | Journal size (bytes) | Trending up rapidly |
| ReadIOs | Read I/O count | Spike = unindexed queries |
| WriteIOs | Write I/O count | Monitor write throughput |
| OccConflictExceptions | Optimistic concurrency conflicts | > 5% of commits |

**Key alert:** `OccConflictExceptions` > 5% of commits indicates
concurrent writes to the same document. Redesign the workload.

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

### Ledger creation fails with "permissions mode not supported"
- Ensure the permissions mode is `STANDARD` or `ALLOW_ALL`.

### Cannot delete a ledger
- Deletion protection is enabled. Disable it first with
  `update-ledger --no-deletion-protection`, then call `delete-ledger`.

### PartiQL queries are slow
- Missing indexes. Create indexes on fields used in WHERE clauses.

### Journal export fails
- Check the IAM role has `s3:PutObject` on the target bucket. Verify the
  S3 bucket policy allows the QLDB service principal.

### Kinesis stream not receiving data
- Verify the stream is active. Check the IAM role has
  `kinesis:PutRecord` on the stream. Verify the stream's start time is
  within the journal's history.

### OccConflictExceptions spike
- Concurrent transactions are writing to the same document. Redesign
  the workload: batch writes, avoid concurrent updates.

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
