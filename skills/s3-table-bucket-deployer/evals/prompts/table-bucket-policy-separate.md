# Eval: table-bucket-policy-separate

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — put-table-bucket-policy with s3tables actions (NOT s3 actions), cross-account read grant, separation from regular S3 bucket policy noted

## Prompt

Create an S3 table bucket named shared-tables in us-east-1
account 123456789012. Create namespace marketing. Create an
Iceberg v2 table named campaigns. Apply a table bucket policy
that grants account 999999999999 read access (GetTable,
ListTables, ListNamespaces, GetNamespace, GetTableBucket).
Tags: Environment=production, Shared=true.
