# Error Handling (load on demand) — DynamoDB Table Deployer

Error-handling deep dives moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)

### Table already exists (`ResourceInUseException`)

```bash
aws dynamodb describe-table --table-name <name>
```

- If configuration matches intent: the table is already provisioned
  correctly. Skip to verification and emit READY_TO_DEPLOY.
- If configuration differs: decide whether to `update-table` (mutable
  settings: capacity, PITR, TTL, streams, table class, deletion
  protection) or create a NEW table with the correct schema (immutable
  settings: partition/sort key, LSIs). Key schema changes REQUIRE
  create-new → backfill → cutover. NEVER attempt to `delete-table` then
  `create-table` to "fix" a schema mismatch — data loss.

### GSI creation fails during backfill

When adding a GSI to an existing table (`update-table
--global-secondary-index-updates`), DynamoDB backfills the index from
the base table. The GSI enters `CREATING` state (can take minutes to
hours for large tables).

**If the backfill fails** (GSI status flips to `DELETING` or table stuck
in `UPDATING`):

1. Check CloudTrail for `LimitExceededException` — the account may have
   too many concurrent GSI backfills (account-level soft limit).
2. Wait for the GSI to finish auto-cleanup (it will reach `DELETING` then
   disappear).
3. Retry with a smaller `ProjectionType` (`KEYS_ONLY` instead of `ALL`)
   to reduce backfill write load.
4. For PROVISIONED tables, temporarily raise the GSI's WCU during
   backfill to avoid throttling the base table during index population.

**NEVER** delete the base table to "fix" a stuck GSI backfill. The
backfill will complete or the GSI will be auto-deleted; either way the
base table data is safe. Monitor with:

```bash
aws dynamodb describe-table --table-name <name> \
  --query 'Table.GlobalSecondaryIndexes[*].[IndexName,IndexStatus,Backfilling]'
```

### PITR enable fails

- **`AccessDeniedException`**: the caller lacks
  `dynamodb:UpdateContinuousBackups`. This is a separate IAM permission
  from `dynamodb:UpdateTable` — add it to the caller's policy.
- **`ValidationException`**: the table was created within the last few
  minutes and is not yet `ACTIVE`. Wait for `TableStatus = ACTIVE` and
  retry.
- **PITR already enabled**: the call is idempotent — returns success with
  no change. No error to handle.

### Autoscaling registration fails

- **"Min capacity must be less than or equal to max capacity"**: check
  that `--min-capacity` < `--max-capacity`. Common typo.
- **"The scalable target already exists"**: the target was previously
  registered. Re-issuing `register-scalable-target` is safe (upsert-like
  for existing targets with the same dimensions). To change dimensions,
  `deregister-scalable-target` first.
- **GSI autoscaling `ResourceNotFoundException`**: the GSI name is wrong
  or the GSI is still `CREATING`. Verify with `describe-table` and
  register autoscaling only after the GSI reaches `ACTIVE`.
