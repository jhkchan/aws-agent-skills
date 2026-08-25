# Error Handling — Redshift Data API Deployer

Data API error deep dives and recovery steps moved verbatim from SKILL.md. Loaded on demand.

## Error handling — API failures and recovery

### ExecuteStatement returns "Cluster not found"
- The cluster identifier is wrong or the cluster does not exist. Verify
  with `aws redshift describe-clusters`.

### DescribeStatement returns "AccessDenied"
- The IAM role lacks `redshift-data:DescribeStatement`. Add the
  permission to the Lambda execution role.

### GetStatementResult returns "Statement result expired"
- More than 24 hours have passed since FINISHED. Results are gone.
  Re-run the query or use UNLOAD to persist to S3.

### Statement stays in SUBMITTED indefinitely
- The cluster may be paused or the WLM queue is full. Check cluster
  status with `aws redshift describe-clusters`. For Serverless, the
  workgroup may be scaling up.

### BatchExecuteStatement partially succeeds
- The batch is NOT transactional. Earlier statements may have committed
  before a later statement failed. Wrap in BEGIN/COMMIT for atomicity.

### Lambda timeout during polling
- The query takes longer than Lambda's 15-minute timeout. Switch to the
  EventBridge async pattern (WithEvent=True + EventBridge rule).
