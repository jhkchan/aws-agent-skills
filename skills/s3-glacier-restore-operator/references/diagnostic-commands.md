# Diagnostic Commands — s3-glacier-restore-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Verification commands


```bash
# Single object restore status
aws s3api head-object --bucket <bucket> --key <key> --query 'Restore'

# Wait for restore completion (single object)
aws s3api wait object-restored --bucket <bucket> --key <key>

# Batch Operations job status
aws s3control describe-job --account-id <account> --job-id <job-id> \
  --query 'Job.{Status:Status,Progress:ProgressSummary}'

# List Batch Operations jobs in an account
aws s3control list-jobs --account-id <account> --operation S3RestoreObject

# Verify object is readable after restore
aws s3api get-object --bucket <bucket> --key <key> /tmp/test.out && echo OK

# Verify lifecycle rule will not re-archive promoted objects
aws s3api get-bucket-lifecycle-configuration --bucket <bucket>
```
