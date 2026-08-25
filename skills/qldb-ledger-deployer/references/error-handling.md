# Error Handling — QLDB Ledger Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


## Error handling

### Ledger creation fails with "permissions mode not supported"
- Ensure the permissions mode is `STANDARD` or `ALLOW_ALL`.

### Cannot delete a ledger
- Deletion protection is enabled. Disable it first with
  `update-ledger --no-deletion-protection`, then call `delete-ledger`.

### PartiQL queries are slow
- Missing indexes. Create indexes on fields used in WHERE clauses.

### Journal export fails
- Check the IAM role has `s3:PutObject` on the target bucket. Verify the
  S3 bucket policy allows the QLDB service principal.

### Kinesis stream not receiving data
- Verify the stream is active. Check the IAM role has
  `kinesis:PutRecord` on the stream. Verify the stream's start time is
  within the journal's history.

### OccConflictExceptions spike
- Concurrent transactions are writing to the same document. Redesign
  the workload: batch writes, avoid concurrent updates.
