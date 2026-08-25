# Advanced Patterns — QLDB Ledger Deployer

Deep-dive material moved out of the SKILL.md body so the procedure stays scannable. Loaded on demand.


## Common misconceptions (from Mindset)

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


## Configuration dependency graph — sequencing notes

QLDB configurations are NOT independent. The ledger must exist before
tables. Tables must exist before indexes. The permissions mode and
deletion protection are set at creation. Use this graph to sequence
provisioning.


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
