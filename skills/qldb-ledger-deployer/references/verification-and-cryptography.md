# Cryptographic Verification and Hash Chains — QLDB Ledger Deployer

Deep reference on QLDB's cryptographic verification system (digests,
proofs, SHA-256 hash chains, Merkle tree structure), the verification
workflow, and how to integrate verification into compliance workflows.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## The cryptographic foundation

### How the immutable journal works

QLDB uses an append-only journal where every transaction is
cryptographically linked to the previous one via SHA-256 hashes:

```text
Block 0 (genesis)
  ├── Block Hash: SHA-256(block_0_contents)
  └── Transactions: [txn_A, txn_B]

Block 1
  ├── Block Hash: SHA-256(block_1_contents + block_0_hash) ← LINKED
  └── Transactions: [txn_C]

Block 2
  ├── Block Hash: SHA-256(block_2_contents + block_1_hash) ← LINKED
  └── Transactions: [txn_D, txn_E]

  Tampering with Block 1:
    → Block 1 hash changes
    → Block 2 hash changes (includes block 1 hash)
    → Block 3 hash changes (includes block 2 hash)
    → ALL subsequent blocks are invalidated
    → Detected by comparing against any stored digest
```

### Merkle tree structure

The digest is built on a Merkle-like tree of block hashes:

```text
                    Root Hash (= Digest)
                   /                    \
          Hash(L + R)                Hash(L + R)
         /          \               /          \
    Hash(B0)    Hash(B1)      Hash(B2)    Hash(B3)
       |           |              |           |
    Block 0     Block 1       Block 2     Block 3

  To prove Block 1 belongs to the digest:
    1. Start with Hash(B1) (the revision hash)
    2. Combine with Hash(B0): SHA-256(Hash(B0) + Hash(B1)) = Hash(L+R)
    3. Combine with right sibling: SHA-256(Hash(L+R) + Hash(R))
    4. Result should equal the digest (root hash)
    5. The "proof" is the list of sibling hashes needed to walk this path
```

## Digests

### What is a digest?

A digest is a SHA-256 hash representing the entire state of the journal
at a specific point in time (the "digest tip address"). It is the root
hash of the Merkle tree of all blocks up to that point.

```bash
# Request a digest
aws qldb get-digest \
  --name audit-ledger \
  --region us-east-1
```

Response:

```json
{
  "Digest": "base64-encoded SHA-256 hash",
  "DigestTipAddress": {
    "IonText": "{strandId:\"ABC123...\",sequenceNo:42}"
  }
}
```

### Digest best practices

```text
1. Request digests PERIODICALLY (daily or weekly)
   → Each digest captures the journal state at that point
   → Store digests externally (not in the same ledger!)

2. Store digests in a SEPARATE, SECURE store
   → S3 with Object Lock (WORM storage)
   → AWS Backup vault with vault lock
   → External key management system
   → Purpose: if the ledger is compromised, the stored digest
     remains untampered and can prove prior integrity

3. Use digests as VERIFICATION BASELINES
   → When an auditor asks "prove this data hasn't changed since August"
   → Retrieve the August digest from external storage
   → Use get-revision with proof against that digest
   → Mathematical proof: the revision belongs to the digest's hash chain

4. Digests are ON-DEMAND (not stored in QLDB itself)
   → You must request and store them yourself
   → If you never request digests, you lose the ability to verify
     retroactively (you can still request current digests, but cannot
     get a digest for a past date)
```

### Automated digest collection (Lambda + EventBridge)

```python
import boto3
import json
from datetime import datetime

qldb = boto3.client('qldb')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Triggered daily by EventBridge schedule
    ledger_name = 'audit-ledger'

    # Request the current digest
    digest_response = qldb.get_digest(Name=ledger_name)

    # Store in S3 with Object Lock
    timestamp = datetime.utcnow().strftime('%Y-%m-%d')
    key = f'digests/{ledger_name}/{timestamp}.json'

    s3.put_object(
        Bucket='qldb-digest-store',
        Key=key,
        Body=json.dumps({
            'ledger': ledger_name,
            'timestamp': timestamp,
            'digest': digest_response['Digest'],
            'digest_tip_address': digest_response['DigestTipAddress']['IonText']
        }),
        ContentType='application/json'
    )

    print(f"Digest stored: s3://qldb-digest-store/{key}")
    return {'statusCode': 200}
```

## Proofs

### What is a proof?

A proof is the list of sibling hashes needed to verify that a specific
document revision belongs to a given digest. It is the Merkle path from
the revision's leaf hash to the root hash (digest).

```bash
# Step 1: Get the block address of the document revision
aws qldb execute-statement \
  --ledger-name audit-ledger \
  --statement "SELECT blockAddress FROM history(transactions) AS h WHERE h.data.transactionId = 'txn-001'" \
  --region us-east-1

# Step 2: Get the revision with proof against the digest
aws qldb get-revision \
  --name audit-ledger \
  --block-address '{"IonText":"{strandId:\"ABC123\",sequenceNo:42}"}' \
  --document-id "DOCUMENT-ID-FROM-STEP-1" \
  --digest-tip-address '{"IonText":"{strandId:\"ABC123\",sequenceNo:100}"}' \
  --region us-east-1
```

Response:

```json
{
  "Revision": {
    "IonText": "{ data: { transactionId: 'txn-001', amount: 1500.0, ... }, hash: '...' }"
  },
  "Proof": {
    "IonText": "[{ hash: 'abc...' }, { hash: 'def...' }, ...]"
  }
}
```

### Verifying the proof

```python
import hashlib
import base64

def verify_proof(revision_hash_bytes, proof_hashes, expected_digest):
    """
    Walk the Merkle proof chain from revision hash to the digest.

    Args:
        revision_hash_bytes: SHA-256 hash of the revision (bytes)
        proof_hashes: List of sibling hashes from the proof (bytes each)
        expected_digest: The digest to compare against (bytes)

    Returns:
        True if the computed hash matches the digest, False otherwise.
    """
    computed = revision_hash_bytes

    for sibling in proof_hashes:
        # QLDB sorts the pair before hashing (Merkle tree ordering)
        if computed < sibling:
            combined = computed + sibling
        else:
            combined = sibling + computed
        computed = hashlib.sha256(combined).digest()

    return computed == expected_digest

# Usage
revision_hash = base64.b64decode(revision_data['hash'])
proof = [base64.b64decode(h) for h in proof_list]
digest = base64.b64decode(stored_digest)

is_verified = verify_proof(revision_hash, proof, digest)
if is_verified:
    print("VERIFIED: Document has not been tampered with")
else:
    print("TAMPERED: Hash chain broken (should never happen in QLDB)")
```

## Verification workflow for compliance audits

```text
Compliance audit verification flow:

  1. Auditor requests proof that transaction txn-001 was not modified
     since August 1, 2026.

  2. Retrieve the August 1 digest from external storage:
     s3://qldb-digest-store/audit-ledger/2026-08-01.json
     → Contains: digest hash + digest tip address

  3. Request the revision and proof from QLDB:
     aws qldb get-revision \
       --name audit-ledger \
       --block-address <txn-001 block address> \
       --document-id <txn-001 document id> \
       --digest-tip-address <August 1 digest tip>

  4. Verify the proof mathematically:
     Compute SHA-256 chain from revision hash through proof siblings
     Compare the result to the August 1 digest

  5. If match: mathematical proof that txn-001 was unchanged since Aug 1
     Provide to auditor as compliance evidence.

  Expert rule:
    This is the core value of QLDB.
    No other AWS database provides cryptographic proof of immutability.
    If you are not using digests and proofs, consider DynamoDB instead.
```

## Terraform examples

```hcl
# QLDB Ledger with STANDARD permissions and deletion protection
resource "aws_qldb_ledger" "audit" {
  name                 = "audit-ledger"
  permissions_mode     = "STANDARD"
  deletion_protection  = true
  kms_key              = aws_kms_key.qldb.arn
  tags = {
    Environment = "production"
    Application = "audit"
    Compliance  = "SOX"
  }
}

# KMS key for QLDB
resource "aws_kms_key" "qldb" {
  description             = "KMS key for QLDB audit-ledger"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "qldb" {
  name          = "alias/qldb-audit"
  target_key_id = aws_kms_key.qldb.key_id
}

# IAM role for journal export to S3
resource "aws_iam_role" "qldb_export" {
  name = "QLDBExportRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "qldb.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "qldb_export_s3" {
  name = "QLDBExportS3Policy"
  role = aws_iam_role.qldb_export.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.qldb_export.arn,
          "${aws_s3_bucket.qldb_export.arn}/*"
        ]
      }
    ]
  })
}

# S3 bucket for journal exports (with Object Lock for WORM)
resource "aws_s3_bucket" "qldb_export" {
  bucket = "qldb-audit-export"
}

resource "aws_s3_bucket_object_lock_configuration" "qldb_export" {
  bucket = aws_s3_bucket.qldb_export.id
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 2555  # 7 years for SOX compliance
    }
  }
}
```


## Step 10 — Cryptographic verification: digest and proof commands

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
