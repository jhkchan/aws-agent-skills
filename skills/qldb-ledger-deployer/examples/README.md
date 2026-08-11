# End-to-End Example: QLDB Ledger Deployment

A walkthrough showing how to use the `qldb-ledger-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production QLDB ledger for a compliance audit
system with STANDARD permissions mode, deletion protection, KMS
encryption, journal export to S3, streaming to Kinesis, and
cryptographic verification. The ledger needs:

- Ledger name: audit-ledger
- Permissions mode: STANDARD
- Deletion protection: enabled
- KMS key: arn:aws:kms:us-east-1:123456789012:key/abc123
- Tables: transactions, accounts, audit_log
- Indexes: transactions(transactionId, fromAccount), accounts(accountId)
- Journal export to S3: bucket qldb-audit-export
- Stream to Kinesis: stream qldb-audit-stream
- Tags: Environment=production, Application=audit, Compliance=SOX

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-qldb-ledger
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a QLDB ledger named audit-ledger with STANDARD
      permissions mode, deletion protection, KMS encryption.
      Tables transactions, accounts, audit_log. Indexes on
      transactionId and accountId. Set up S3 export and Kinesis
      streaming for compliance."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a qldb ledger"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the ledger
aws qldb create-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --kms-key arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --region us-east-1

# Wait for the ledger to become active
aws qldb wait ledger-active \
  --name audit-ledger \
  --region us-east-1
```

---

## Step 4 — Create tables and indexes via PartiQL

```bash
# Using the QLDB shell
qldb --ledger audit-ledger --region us-east-1
```

```sql
-- Create tables
CREATE TABLE transactions;
CREATE TABLE accounts;
CREATE TABLE audit_log;

-- Create indexes (BEFORE inserting data)
CREATE INDEX ON transactions (transactionId);
CREATE INDEX ON transactions (fromAccount);
CREATE INDEX ON accounts (accountId);

-- Insert sample data
INSERT INTO transactions
{
    transactionId: 'txn-001',
    amount: 1500.00,
    currency: 'USD',
    fromAccount: 'acc-aaa',
    toAccount: 'acc-bbb',
    timestamp: `2026-08-05T12:00:00Z`,
    status: 'pending'
};

-- Verify data
SELECT * FROM transactions WHERE transactionId = 'txn-001';

-- History query (all revisions)
SELECT * FROM history(transactions) AS h
WHERE h.data.transactionId = 'txn-001';
```

---

## Step 5 — Set up journal export to S3

```bash
# Create IAM role for QLDB export
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

# Attach S3 write policy
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

# Export the journal
aws qldb export-journal-to-s3 \
  --name audit-ledger \
  --export-name audit-export-2026-08 \
  --role-arn arn:aws:iam::123456789012:role/QLDBExportRole \
  --output-s3-prefix s3://qldb-audit-export/audit-ledger/2026-08/ \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-31T23:59:59Z \
  --region us-east-1
```

---

## Step 6 — Set up streaming to Kinesis

```bash
# Create Kinesis stream
aws kinesis create-stream \
  --stream-name qldb-audit-stream \
  --shard-count 1 \
  --region us-east-1

aws kinesis wait stream-active \
  --stream-name qldb-audit-stream \
  --region us-east-1

# Create IAM role for QLDB streaming
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

# Attach Kinesis write policy
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

# Start the QLDB stream
aws qldb stream-journal-to-kinesis \
  --ledger-name audit-ledger \
  --role-arn arn:aws:iam::123456789012:role/QLDBStreamRole \
  --inclusive-start-time 2026-08-05T00:00:00Z \
  --exclusive-end-time 2026-12-31T23:59:59Z \
  --kinesis-configuration StreamName=qldb-audit-stream,AggregationEnabled=true \
  --stream-name audit-ledger-cdc-stream \
  --region us-east-1
```

---

## Step 7 — Cryptographic verification

```bash
# Request a digest (point-in-time hash of the entire journal)
aws qldb get-digest \
  --name audit-ledger \
  --region us-east-1
# Save the digest and digest tip address

# Get a document revision with proof
# First, find the block address via PartiQL:
aws qldb execute-statement \
  --ledger-name audit-ledger \
  --statement "SELECT blockAddress FROM history(transactions) AS h WHERE h.data.transactionId = 'txn-001'" \
  --region us-east-1

# Then get the revision with proof against the digest
aws qldb get-revision \
  --name audit-ledger \
  --block-address '{"IonText":"{strandId:\"abc\",sequenceNo:42}"}' \
  --document-id "doc-123" \
  --digest-tip-address '{"IonText":"{strandId:\"abc\",sequenceNo:100}"}' \
  --region us-east-1
# The response includes Proof hashes — verify the chain mathematically
```

---

## Step 8 — Post-deployment verification

```bash
# Ledger status
aws qldb describe-ledger \
  --name audit-ledger \
  --query 'State' --region us-east-1
# Expected: ACTIVE

# Kinesis streams for this ledger
aws qldb list-journal-kinesis-streams-for-ledger \
  --ledger-name audit-ledger \
  --region us-east-1

# S3 exports for this ledger
aws qldb list-journal-s3-exports-for-ledger \
  --name audit-ledger \
  --region us-east-1

# CloudWatch: command execution latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/QLDB \
  --metric-name CommandExecutionLatency \
  --dimensions Name=LedgerName,Value=audit-ledger \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Permissions mode | Uses ALLOW_ALL for simplicity | STANDARD enforced | ALLOW_ALL grants full CRUD to all principals; defeats ledger purpose |
| Deletion protection | Not enabled | Enabled | Prevents catastrophic accidental deletion of immutable journal |
| Indexes | Created after inserting data | Created BEFORE inserts | QLDB has no query optimizer; unindexed queries are full scans |
| KMS key | Uses AWS-owned default | Customer-managed key | Customer key allows rotation and policy control |
| Digest + proof | Not documented | Full verification workflow | Cryptographic proof is QLDB's core value — integrate into compliance |
| Export vs stream | Not planned at creation | Both configured | Export for audit, stream for real-time CDC — different purposes |

---

## Related artifacts

- **Skill definition:** `skills/qldb-ledger-deployer/SKILL.md`
- **Verification and cryptography guide:** `skills/qldb-ledger-deployer/references/verification-and-cryptography.md`
- **Export and streaming guide:** `skills/qldb-ledger-deployer/references/export-and-streaming.md`
- **Slash command:** `commands/aws/deploy-qldb-ledger.md`
- **Eval suite:** `skills/qldb-ledger-deployer/evals/evals.json`
- **Legacy test cases:** `skills/qldb-ledger-deployer/eval/test-cases.yaml`
