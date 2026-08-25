# Diagnostic Commands — Athena Query Optimizer

Load-on-demand pre-flight and diagnostic CLI moved verbatim from SKILL.md.

## Step 1: Validate input and data sufficiency — data-gathering CLI

Gather DDL and query history:

```bash
# Table DDL and properties:
aws glue get-table --database-name <db> --name <table> \
  --query 'Table.{Storage:StorageDescriptor,Partitions:Parameters,Compression:Parameters.compression}'

# Query history (last 50 queries on this workgroup):
aws athena list-query-executions --work-group <wg> --max-results 50 \
  --query 'QueryExecutionIds'

# Batch get execution details (data scanned, runtime, status):
aws athena batch-get-query-execution \
  --query-execution-ids <id1> <id2> <id3> \
  --query 'QueryExecutions[*].{Query:Query,Scanned:Statistics.DataScannedInBytes,Runtime:Statistics.EngineExecutionTimeInMillis,State:Status.State}'
```
