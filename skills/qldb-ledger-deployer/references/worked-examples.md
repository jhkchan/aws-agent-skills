# Worked Examples — QLDB Ledger Deployer

Filled-in configuration examples moved out of the SKILL.md body. Loaded on demand.


## Step 2 — STANDARD mode IAM policy example

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


## Step 5 — Table creation and document model (Ion): SQL examples

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


## Step 6 — PartiQL query examples

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
