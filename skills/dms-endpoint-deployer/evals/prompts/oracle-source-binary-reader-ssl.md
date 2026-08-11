# Eval: oracle-source-binary-reader-ssl

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Oracle source with Binary Reader, archived log tuning, verify-full SSL with imported certificate, supplemental logging prerequisite noted

## Prompt

Create a DMS source endpoint for Oracle at
oracle-prod.example.com port 1521, SID ORCL, us-east-1. Use
Binary Reader for CDC (useLogminerReader=N,
AdditionalArchivedLogDestId=1). SSL mode verify-full with
certificate oracle-ca-cert. KMS key
arn:aws:kms:us-east-1:123456789012:key/oracle-key. Replication
instance rep-instance-prod. Tags: Environment=production,
Engine=oracle.
