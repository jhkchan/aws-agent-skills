# Eval: cryptographic-verification

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — digest + proof hash chain verification workflow documented, STANDARD permissions, deletion protection

## Prompt

Create a QLDB ledger named compliance-ledger in us-east-1 for
regulatory compliance with cryptographic verification. Permissions
mode STANDARD. Deletion protection enabled. KMS key
arn:aws:kms:us-east-1:123456789012:key/verify123. I need the
full digest and proof verification workflow documented. Tables:
compliance_records. Indexes on compliance_records(recordId).
Tags: Environment=production, Compliance=HIPAA.
