# Error Handling (load on demand) — Data Exchange Dataset Deployer

Failure-mode deep dives (export job ERROR, auto-export not triggering,
invisible revisions, Lake Formation access, API auth) moved verbatim from
SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)



### Export job fails with ERROR state
- The IAM role may lack `s3:PutObject` on the destination bucket.
  Check the job errors array for IAM-related messages. Verify the
  export job's role has the correct S3 permissions.

### Auto-export not triggering on new revisions
- The EventBridge rule may not match the event pattern. Verify the
  rule's event pattern includes the correct data-set-id. Check
  CloudWatch Metrics for EventBridge invocations. Ensure the Lambda
  function has permission to be invoked by EventBridge.

### Revision not visible to subscriber
- The revision may not be finalized. Only FINALIZED revisions are
  visible to subscribers. Verify revision state via
  `get-revision`. If the revision is still DRAFT, the provider must
  finalize it.

### Lake Formation table not accessible
- The S3 location may not be registered with Lake Formation. Run
  `register-resource` for the S3 path. Verify the Data Catalog
  table points to the correct S3 location. Check LF grants for the
  principal.

### API asset authentication fails
- The API signing key may be expired. Regenerate the Data Exchange
  API key via the console or API. Verify the API URL from the asset
  details. Ensure rate limits are not exceeded.


