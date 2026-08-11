---
name: qldb-ledger-deployer
description: >-
  Provisions Amazon QLDB (Quantum Ledger Database) ledgers with
  production defaults: ledger creation (create-ledger), permissions mode
  (STANDARD vs ALLOW_ALL), deletion protection, KMS encryption, PartiQL
  query language, Amazon Ion data format, journal export to S3, stream
  to Kinesis Data Streams, cryptographic verification (digest + proof),
  revision hash chains, indexed fields, table creation, document model,
  and CloudWatch metrics. Emits a READY_TO_DEPLOY checklist with
  verification commands. Use when creating a QLDB ledger, configuring
  permissions mode, enabling deletion protection, setting up journal
  export, streaming to Kinesis, verifying data integrity with digests
  and proofs, creating tables and indexes, or writing PartiQL queries.
  Triggers: create qldb ledger, qldb permissions mode, qldb deletion
  protection, qldb journal export, qldb kinesis stream, qldb
  cryptographic verification, qldb digest, qldb proof, qldb partiql,
  qldb ion data format, qldb hash chain, qldb index, qldb table
  creation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with qldb access.
  Works with Terraform aws_qldb_ledger / aws_qldb_stream /
  aws_qldb_s3_export_task resources and the AWS SDK for PartiQL
  (qldb-session, qldb APIs).
keywords:
  - aws
  - qldb
  - quantum ledger database
  - immutable ledger
  - cloudops
  - deploy
  - provisioning
  - partiql
  - amazon ion
  - hash chain
  - cryptographic verification
  - journal export
  - kinesis stream
  - deletion protection
  - digest
  - proof
tags:
  - aws
  - qldb
  - ledger
  - cloudops
  - deploy
  - databases
  - provisioning
  - immutable
  - cryptographic
  - partiql
  - ion
  - hash-chain
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - qldb
    - ledger
    - cloudops
    - deploy
    - databases
    - provisioning
    - immutable
    - cryptographic
    - partiql
    - ion
    - hash-chain
  dependencies:
    - aws-orchestrator
  keywords:
    - create qldb ledger
    - qldb permissions mode
    - qldb deletion protection
    - qldb journal export
    - qldb kinesis stream
    - qldb cryptographic verification
    - qldb digest
    - qldb proof
    - qldb partiql
    - qldb ion data format
    - qldb hash chain
    - qldb index
    - qldb table creation
  when_to_use: >-
    Invoke when the user wants to create an Amazon QLDB ledger, configure
    permissions mode (STANDARD vs ALLOW_ALL), enable deletion protection,
    set up journal export to S3, stream journal data to Kinesis for
    real-time CDC, verify data integrity using cryptographic digests and
    proofs, create tables and indexes, or write PartiQL queries against
    Ion-format documents. Do NOT invoke for Amazon DynamoDB (use DynamoDB
    skills), Amazon DocumentDB (use DocumentDB skills), Amazon Timestream
    (use Timestream skills), or Amazon RDS (use RDS skills).
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
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `QLDB_LEDGER:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

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
| Step 13 — Recent features | Latest |
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
  digest and verifying a proof. This cryptographic guarantee is the
  entire point — if you do not need it, use DynamoDB instead.

- **"ALLOW_ALL permissions mode is fine for simplicity."** It is NOT.
  ALLOW_ALL grants full CRUD to any IAM principal with access to QLDB.
  For a ledger whose entire purpose is immutability and auditability,
  ALLOW_ALL defeats the purpose. ALWAYS use STANDARD permissions mode
  for production, which enforces table-level and field-level IAM
  controls.

- **"I can export or stream the journal later when I need it."** You
  can, but the export/stream should be planned at provisioning time.
  Journal export to S3 is for compliance audit (point-in-time snapshots).
  Streaming to Kinesis is for real-time CDC (continuous). If you wait
  until an audit is requested, you are scrambling. Set up the export
  pipeline and/or stream at creation time.

## Configuration dependency graph (novel heuristic)

QLDB configurations are NOT independent. The ledger must exist before
tables. Tables must exist before indexes. The permissions mode and
deletion protection are set at creation. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Ledger (create-ledger) | permissions mode, deletion protection, KMS key | permissions mode and deletion protection can be modified after creation; KMS key cannot be changed without recreating the ledger | tables, journal, exports, streams |
| Permissions mode | ledger exists | STANDARD enforces IAM-based table/field controls; ALLOW_ALL grants full access | access control |
| Deletion protection | ledger exists | when enabled, ledger CANNOT be deleted until disabled; prevents accidental deletion | safety |
| KMS key | key exists (if customer-managed) | KMS key is immutable after ledger creation (must recreate ledger to change) | encryption at rest |
| Table creation | ledger is active | QLDB does not enforce a schema; documents in the same table can have different fields | data storage |
| Indexes | table exists | creating an index on a large table takes time; queries without indexes are full scans | query performance |
| Journal export to S3 | ledger exists; S3 bucket with write access | export is asynchronous; can take hours for large journals | compliance audit, data lake |
| Stream to Kinesis | ledger exists; Kinesis stream exists; IAM role with qldb:SendCommand + kinesis:PutRecord | stream is continuous; covers a configurable time range; stream must be started with inclusive start time | real-time CDC |
| Digest | ledger exists | digest is a point-in-time hash of the entire journal; cannot be generated retroactively for past dates without re-requesting | cryptographic verification baseline |
| Proof | digest exists; document revision known | proof verifies that a specific revision belongs to the digest's hash chain | tamper detection |

**The permissions-mode and deletion-protection rows are the ones a
baseline model misses.** ALLOW_ALL in a production ledger is a security
hole. Missing deletion protection risks catastrophic data loss. The
procedure below forces an explicit decision on each.

**Cross-dependency gotchas:**
- The permissions mode is set at ledger creation but can be modified
  later via `update-ledger`. Switching from ALLOW_ALL to STANDARD is
  possible but existing IAM policies must be in place first.
- Deletion protection prevents deletion even with administrator
  privileges. To delete a protected ledger, first disable protection,
  then delete.
- Journal export requires an IAM role that QLDB can assume to write to
  S3. The S3 bucket policy must allow the QLDB service principal.
- Kinesis streaming requires the stream to exist and the IAM role to
  have `kinesis:PutRecord` permissions before starting the QLDB stream.
- Digests are generated on-demand. You should periodically request
  digests and store them externally as verification baselines.

## Expert heuristic: immutable journal hash chain verification

A baseline model says "QLDB stores data immutably." The correct
heuristic recognizes that immutability is only valuable if you can
PROVE it — and the proof mechanism (digest + proof) must be integrated
into your verification workflow.

```text
QLDB cryptographic verification flow:

  1. Request a DIGEST (a Merkle-like hash of the entire journal at time T):
     digest = qldb.get_digest(ledger_name)
     → Returns: SHA-256 hash representing the entire journal state at time T

  2. Retrieve a document revision (the current state of a document):
     revision = qldb.get_revision(ledger_name, document_id, block_address)
     → Returns: the document data + its hash

  3. Request a PROOF (the hash chain from the revision to the digest):
     proof = qldb.get_revision(ledger_name, document_id, block_address, digest)
     → Returns: array of hashes forming the path from revision to digest

  4. Verify: hash the revision, walk the proof chain, compare to the digest:
     computed_hash = sha256(revision)
     for node in proof:
         computed_hash = sha256(computed_hash + node)
     assert computed_hash == digest
     → If match: document is VERIFIED (untampered)
     → If mismatch: document has been TAMPERED (should never happen in QLDB)

  Expert rule:
    Request digests periodically (e.g., daily).
    Store digests in a separate, secure store (S3 with Object Lock).
    Use proofs to verify any document on-demand.
    This proves to auditors that data has not been modified.
```

**Key implication:** the entire value proposition of QLDB is the
cryptographic proof. If you never request digests or proofs, you are
paying for immutability guarantees you are not using. Integrate
verification into your compliance workflow.

## Expert heuristic: stream for real-time CDC vs export for compliance audit

QLDB provides two data extraction mechanisms with different purposes:

```text
Journal export to S3:
  Purpose: compliance audit, point-in-time snapshot, data lake ingestion
  Trigger: on-demand or scheduled (e.g., nightly)
  Output: S3 objects in Ion format (journal_kit will parse)
  Latency: hours (for large journals)
  Use when: you need a full copy of the journal for audit/regulatory purposes

Stream to Kinesis Data Streams:
  Purpose: real-time change data capture (CDC)
  Trigger: continuous (started with a start time, runs until ended)
  Output: Kinesis records (JSON/Ion encoded revision + metadata)
  Latency: near real-time (seconds)
  Use when: downstream systems need to react to changes immediately

Expert rule:
  Export to S3 = compliance audit (batch, periodic, full journal)
  Stream to Kinesis = real-time CDC (continuous, incremental, event-driven)
  Use BOTH for a complete data pipeline: stream for real-time, export for audit trail.
```

## Expert heuristic: STANDARD permissions mode enforcement

```text
Permissions mode comparison:

  ALLOW_ALL (default for backward compatibility, NOT recommended):
    Every IAM principal with qldb:SendCommand has FULL CRUD on ALL tables.
    No table-level or field-level control.
    Equivalent to granting *:* on the ledger.
    Risk: any compromised credential can modify or delete ledger data.

  STANDARD (recommended for ALL production ledgers):
    IAM policies control access at the TABLE and FIELD level.
    Example policy allows INSERT on 'transactions' table but not DELETE.
    Example policy allows SELECT on 'ssn' field but not UPDATE.
    Enforces least privilege on immutable data.

  Expert rule:
    ALWAYS use STANDARD permissions mode.
    Define IAM policies per table and per operation BEFORE switching.
    ALLOW_ALL is acceptable only for development/testing ledgers.
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

# Create a ledger with ALLOW_ALL (NOT recommended for production)
aws qldb create-ledger \
  --name dev-ledger \
  --permissions-mode ALLOW_ALL \
  --no-deletion-protection \
  --region us-east-1
```

**Modify permissions mode (after creation):**

```bash
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
      "Action": "qldb:PartiQLInsert",
      "Resource": "arn:aws:qldb:us-east-1:123456789012:ledger/audit-ledger/table/*"
    },
    {
      "Effect": "Allow",
      "Action": "qldb:PartiQLSelect",
      "Resource": "arn:aws:qldb:us-east-1:123456789012:ledger/audit-ledger/table/*"
    }
  ]
}
```

**Expert rule:** ALWAYS use STANDARD for production. ALLOW_ALL grants
full CRUD to anyone with `qldb:SendCommand`, defeating the purpose of
an immutable ledger.

## Step 3 — Deletion protection

```bash
# Create with deletion protection enabled
aws qldb create-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --region us-east-1

# Enable deletion protection on an existing ledger
aws qldb update-ledger \
  --name audit-ledger \
  --deletion-protection \
  --region us-east-1

# Disable deletion protection (required before deleting a ledger)
aws qldb update-ledger \
  --name audit-ledger \
  --no-deletion-protection \
  --region us-east-1
```

**Expert rule:** deletion protection prevents deletion even with
administrator privileges. Always enable it for production ledgers. To
delete, first disable protection, then call `delete-ledger`.

## Step 4 — KMS encryption

```bash
# Create ledger with customer-managed KMS key
aws qldb create-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --kms-key arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --region us-east-1
```

**Critical:** the KMS key is immutable after ledger creation. To change
the encryption key, you must create a new ledger and migrate data.
Choose the key carefully at creation. If `--kms-key` is omitted, QLDB
uses an AWS-owned key.

## Step 5 — Table creation and document model (Ion)

QLDB stores data in Amazon Ion format — a rich, self-describing data
format that is a superset of JSON. Tables are schemaless (documents in
the same table can have different fields).

**Create tables via PartiQL (using the QLDB shell or SDK):**

```bash
# Using the QLDB shell
qldb --ledger audit-ledger --region us-east-1

# Inside the shell:
```

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
    metadata: {
        source: 'mobile-app',
        ipAddress: '192.168.1.1',
        notes: 'Transfer for invoice #12345'
    }
};

-- Query documents
SELECT * FROM transactions WHERE transactionId = 'txn-001';

-- Update a document (creates a new revision, old revision preserved)
UPDATE transactions SET status = 'confirmed' WHERE transactionId = 'txn-001';
```

**Ion data format highlights:**
- Supports typed values: strings, integers, floats, timestamps, blobs
- Timestamps are first-class types (`2026-08-05T12:00:00Z`)
- Comments with `//` or `/* */`
- S-expressions, annotated values
- JSON is valid Ion (but Ion is richer)

## Step 6 — PartiQL query language

QLDB uses PartiQL — a SQL-compatible query language that handles
semi-structured data. PartiQL extends SQL with the ability to query
nested and schemaless data.

```sql
-- Basic SELECT
SELECT * FROM transactions WHERE amount > 1000;

-- Project specific fields
SELECT transactionId, amount, status FROM transactions;

-- Query nested data (Ion)
SELECT t.transactionId, t.metadata.source
FROM transactions t
WHERE t.metadata.source = 'mobile-app';

-- Aggregate
SELECT COUNT(*) AS total FROM transactions;

-- JOIN tables
SELECT t.transactionId, a.accountName
FROM transactions t, accounts a
WHERE t.fromAccount = a.accountId;

-- ORDER BY and LIMIT
SELECT * FROM transactions
ORDER BY timestamp DESC
LIMIT 10;

-- History query (see all revisions of a document)
SELECT * FROM history(transactions) AS h
WHERE h.data.transactionId = 'txn-001';
```

**History queries** are unique to QLDB — they return ALL revisions of a
document, showing the complete mutation history. This is the audit trail.

## Step 7 — Indexed fields

QLDB indexes are critical for query performance. Without an index, every
query is a full table scan. Indexes must be created explicitly.

```sql
-- Create an index on a single field
CREATE INDEX ON transactions (transactionId);

-- Create an index on another field
CREATE INDEX ON transactions (fromAccount);

-- Create an index on the accounts table
CREATE INDEX ON accounts (accountId);
```

**Verify indexes:**

```bash
# List indexes via PartiQL
SELECT * FROM information_schema.user_tables;

# Via AWS CLI
aws qldb list-ledgers --region us-east-1
aws qldb describe-ledger --name audit-ledger --region us-east-1
```

**Indexing rules:**
- Create indexes BEFORE inserting large amounts of data
- Indexes are on a SINGLE field (no compound indexes in QLDB)
- The `documentId` field is automatically indexed
- Queries on unindexed fields are full scans (slow on large tables)
- Index creation on existing data takes time (reindex)

**Expert rule:** create indexes for every field used in WHERE clauses.
QLDB does not have a query optimizer — without an index, performance
degrades linearly with table size.

## Step 8 — Journal export to S3 (compliance audit)

Journal export writes the entire journal (or a time range) to S3 in Ion
format. This is for compliance audit, regulatory snapshots, and data
lake ingestion.

```bash
# Create an IAM role that QLDB assumes to write to S3
aws iam create-role \
  --role-name QLDBExportRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "qldb.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach inline policy for S3 write access
aws iam put-role-policy \
  --role-name QLDBExportRole \
  --policy-name QLDBExportS3Policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
        "Resource": [
          "arn:aws:s3:::qldb-audit-export",
          "arn:aws:s3:::qldb-audit-export/*"
        ]
      }
    ]
  }'

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

**Export output format:** the S3 bucket contains Ion-formatted journal
blocks. Each block includes the block hash, transaction metadata, and
document revisions. The export can be parsed by any Ion-compatible tool.

## Step 9 — Stream to Kinesis (real-time CDC)

QLDB streams journal data to Kinesis Data Streams for real-time change
data capture. This is for downstream systems that need to react to
ledger changes immediately.

```bash
# Prerequisite: create the Kinesis stream
aws kinesis create-stream \
  --stream-name qldb-audit-stream \
  --shard-count 1 \
  --region us-east-1

# Wait for the stream to become active
aws kinesis wait stream-active \
  --stream-name qldb-audit-stream \
  --region us-east-1

# Create an IAM role for QLDB to write to Kinesis
aws iam create-role \
  --role-name QLDBStreamRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "qldb.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach inline policy for Kinesis write access
aws iam put-role-policy \
  --role-name QLDBStreamRole \
  --policy-name QLDBStreamKinesisPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
        "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/qldb-audit-stream"
      }
    ]
  }'

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

**Stream record format:** each Kinesis record contains a JSON/Ion-encoded
journal entry with revision data, metadata, and the hash chain link.
Downstream consumers decode and process these records.

**Expert rule:** use streaming for real-time CDC and export for
compliance audit. They serve different purposes and can run in parallel.

## Step 10 — Cryptographic verification (digest + proof)

Cryptographic verification proves that a document has not been tampered
with since a given point in time. This is QLDB's killer feature.

**Request a digest (point-in-time hash of the entire journal):**

```bash
aws qldb get-digest \
  --name audit-ledger \
  --region us-east-1
```

Response includes:
- `Digest` — SHA-256 hash representing the journal state at the
  requested time
- `DigestTipAddress` — the block address (ledger sequence + hash) that
  the digest covers

**Get a document revision and verify it against the digest:**

```bash
# Step 1: Get the block address of the document
aws qldb execute-statement \
  --ledger-name audit-ledger \
  --statement "SELECT blockAddress FROM history(transactions) AS h WHERE h.data.transactionId = 'txn-001'" \
  --region us-east-1

# Step 2: Get the revision with proof
aws qldb get-revision \
  --name audit-ledger \
  --block-address '{"IonText":"{strandId:\"abc-strand-id\",sequenceNo:42}"}' \
  --document-id "abc-document-id" \
  --digest-tip-address '{"IonText":"{strandId:\"abc-strand-id\",sequenceNo:100}"}' \
  --region us-east-1
```

Response includes:
- `Revision` — the document data
- `Proof` — array of hashes forming the path from the revision to the
  digest

**Verify the proof (Python example):**

```python
import hashlib

def verify_proof(revision_hash, proof_hashes, digest):
    """Walk the proof chain from revision hash to the digest."""
    computed = revision_hash
    for sibling_hash in proof_hashes:
        computed = hashlib.sha256(computed + sibling_hash).digest()
    return computed == digest

# If True: the document is verified (untampered)
# If False: tampering detected (should never happen in QLDB)
```

**Expert rule:** request digests periodically (daily or weekly). Store
them externally (S3 with Object Lock). Use proofs to verify any document
on-demand. This is how you prove data integrity to auditors.

## Step 11 — Revision hash chains

Every revision in QLDB is part of a cryptographic hash chain. Here is
how the chain works:

```text
QLDB journal structure:

  Block N
    ├── Block Hash: SHA-256(Block N contents + previous block hash)
    ├── Transaction 1
    │     ├── Document Revision: {transactionId: 'txn-001', amount: 1500, ...}
    │     └── Revision Hash: SHA-256(revision data)
    └── Transaction 2
          ├── Document Revision: {accountId: 'acc-aaa', ...}
          └── Revision Hash: SHA-256(revision data)

  Block N+1
    ├── Block Hash: SHA-256(Block N+1 contents + Block N hash) ← LINKED
    └── ...

  The chain: each block's hash includes the previous block's hash.
  Modifying any revision changes its hash → changes its block hash →
  breaks every subsequent block hash → detected by digest verification.

  Expert rule:
    The hash chain is the cryptographic foundation.
    Digests summarize the entire chain at a point in time.
    Proves verify individual revisions against digests.
    Together: provable, mathematical immutability.
```

## Step 12 — CloudWatch metrics

| Metric | What it measures | Alert threshold |
|---|---|---|
| CommandExecutionLatency | PartiQL execution time | > 1000ms sustained |
| JournalStorage | Journal size (bytes) | Trending up rapidly |
| IndexedStorage | Index + table size (bytes) | Monitor for growth |
| ReadIOs | Read I/O count | Spike = unindexed queries |
| WriteIOs | Write I/O count | Monitor write throughput |
| SessionRateExceeded | Sessions exceeding limit | > 0 |
| CommitRateExceeded | Commits exceeding limit | > 0 |
| OccConflictExceptions | Optimistic concurrency conflicts | > 5% of commits |

```bash
# Monitor command execution latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/QLDB \
  --metric-name CommandExecutionLatency \
  --dimensions Name=LedgerName,Value=audit-ledger \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average,Maximum \
  --region us-east-1
```

**Key alert:** `OccConflictExceptions` > 5% of commits indicates
concurrent writes to the same document. Redesign the workload to reduce
conflicts (batch writes, different documents).

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **QLDB partiQL performance improvements (2023-2024):** Enhanced
  PartiQL query engine with better join performance and optimized index
  scans. Reduced query latency for common patterns.

- **Journal export to S3 enhancements (2023-2024):** Improved export
  performance with parallel writes and progress tracking. Export now
  supports incremental ranges more efficiently.

- **Kinesis streaming aggregation (2023-2024):** Stream aggregation
  batches multiple revisions into a single Kinesis record, reducing
  per-record costs for high-throughput ledgers.

- **Standard permissions mode maturity (2024-2025):** Enhanced
  field-level IAM controls and audit logging for STANDARD permissions
  mode. Table-level policy granularity improvements.

- **CloudWatch insights (2024-2025):** QLDB CloudWatch Contributor
  Insights for identifying hot partitions and high-frequency document
  access patterns. Improved visibility into query performance.

- **Terraform provider coverage (2025-2026):** The Terraform
  `aws_qldb_ledger`, `aws_qldb_stream`, and `aws_qldb_s3_export_task`
  resources now support full lifecycle management including streaming
  configuration and export scheduling.

## NEVER do these things

1. **NEVER use ALLOW_ALL permissions mode for production.** ALLOW_ALL
   grants full CRUD to anyone with `qldb:SendCommand`. For an immutable
   ledger, this defeats the purpose. ALWAYS use STANDARD.

2. **NEVER deploy a production ledger without deletion protection.**
   Without deletion protection, a single errant `delete-ledger` command
   destroys the entire journal irreversibly. Always enable it.

3. **NEVER skip index creation on fields used in WHERE clauses.** QLDB
   has no query optimizer. Queries on unindexed fields are full table
   scans. Create indexes BEFORE inserting data.

4. **NEVER assume the KMS key can be changed after creation.** The KMS
   key is immutable. Changing encryption requires recreating the ledger.
   Choose carefully at creation time.

5. **NEVER treat QLDB as a general-purpose NoSQL database.** QLDB is
   purpose-built for immutable, cryptographically verified data. If you
   do not need the audit trail or hash chain verification, use DynamoDB
   instead (it is cheaper and faster for general workloads).

6. **NEVER wait until an audit is requested to set up journal export.**
   Export and streaming pipelines should be provisioned at ledger
   creation. Scrambling to export data during an audit is risky and slow.

7. **NEVER store digests in the same ledger they verify.** Digests are
   the verification baseline. Store them in a separate, secure store
   (S3 with Object Lock, or an external system).

8. **NEVER use compound indexes.** QLDB supports only single-field
   indexes. For multi-field queries, create separate indexes on each
   field. QLDB will use the most selective index.

9. **NEVER ignore OccConflictExceptions.** High conflict rates indicate
   concurrent writes to the same document. Redesign the workload (batch
   writes, partition documents differently, reduce write contention).

10. **NEVER delete a ledger without disabling deletion protection
    first.** The `delete-ledger` command fails if deletion protection is
    enabled. Disable it first, then delete.

## Output format

```text
QLDB_LEDGER: <ledger-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Ledger name: <name>
  [✓|✗] Permissions mode: STANDARD | ALLOW_ALL
  [✓|✗] Deletion protection: enabled | disabled
  [✓|✗] KMS encryption: <customer-managed|aws-owned> (<key-id>)
  [✓|✗] Tables: <list>
  [✓|✗] Indexes: <field list per table>
  [✓|✗] Journal export to S3: <configured|none> (bucket: <name>)
  [✓|✗] Stream to Kinesis: <configured|none> (stream: <name>)
  [✓|✗] Cryptographic verification: digest + proof workflow documented
  [✓|✗] Revision hash chain: SHA-256 chained blocks
  [✓|✗] CloudWatch alerts: <metrics list>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws qldb describe-ledger --name <ledger-name> --region <region>
  aws qldb list-journal-kinesis-streams-for-ledger --ledger-name <ledger-name> --region <region>
  aws qldb get-digest --name <ledger-name> --region <region>
```

### Worked example — production audit ledger with STANDARD mode and verification

```text
QLDB_LEDGER: audit-ledger
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Ledger name: audit-ledger
  [✓] Permissions mode: STANDARD
  [✓] Deletion protection: enabled
  [✓] KMS encryption: customer-managed (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Tables: transactions, accounts, audit_log
  [✓] Indexes: transactions(transactionId, fromAccount), accounts(accountId)
  [✓] Journal export to S3: configured (bucket: qldb-audit-export)
  [✓] Stream to Kinesis: configured (stream: qldb-audit-stream)
  [✓] Cryptographic verification: digest + proof workflow documented
  [✓] Revision hash chain: SHA-256 chained blocks
  [✓] CloudWatch alerts: CommandExecutionLatency, OccConflictExceptions, JournalStorage
  [✓] Tags: Environment=production, Application=audit, Compliance=SOX
VERIFICATION_COMMANDS:
  aws qldb describe-ledger --name audit-ledger --region us-east-1
  aws qldb list-journal-kinesis-streams-for-ledger --ledger-name audit-ledger --region us-east-1
  aws qldb get-digest --name audit-ledger --region us-east-1
```

## Error handling

### Ledger creation fails with "permissions mode not supported"
- Ensure the permissions mode is `STANDARD` or `ALLOW_ALL`. Check the
  AWS region supports QLDB and the specified mode.

### Cannot delete a ledger
- Deletion protection is enabled. Disable it first with
  `update-ledger --no-deletion-protection`, then call `delete-ledger`.

### PartiQL queries are slow
- Missing indexes. Create indexes on fields used in WHERE clauses.
  Without indexes, QLDB performs full table scans. Check with
  `information_schema.user_tables`.

### Journal export fails
- Check the IAM role has `s3:PutObject` on the target bucket. Verify
  the S3 bucket policy allows the QLDB service principal. Check the
  export time range is valid (start < end, both within journal history).

### Kinesis stream not receiving data
- Verify the stream is active. Check the IAM role has
  `kinesis:PutRecord` on the stream. Verify the stream's start time is
  within the journal's history. The stream must be started with an
  inclusive start time that is not in the future.

### OccConflictExceptions spike
- Concurrent transactions are writing to the same document. Redesign
  the workload: batch writes, avoid concurrent updates to the same
  document, or use different documents for parallel writes.

### Digest verification fails
- This should never happen in normal operation. If it does, contact AWS
  support immediately — it may indicate a storage-level issue. In
  practice, QLDB's cryptographic guarantees make tampering detectable
  but not possible without breaking the hash chain.

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
- **CloudWatch metrics** — https://docs.aws.amazon.com/qldb/latest/developerguide/monitoring.html
- **Deletion protection** — https://docs.aws.amazon.com/qldb/latest/developerguide/ledger-delete.html
