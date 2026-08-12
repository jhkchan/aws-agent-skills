# Eval: missing-namespace-prerequisite

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — namespace 'identity' does not exist; create-table requires namespace first

## Prompt

Create an S3 table bucket named prod-tables in us-east-1 account
123456789012. Then create an Iceberg v2 table named users in
namespace identity (skip namespace creation). Columns: user_id
(long), email (string), created_at (timestamp). Partition by
day(created_at).
