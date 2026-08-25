# Worked Examples — s3-secure-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Output format (compact template)

```
BUCKET: <bucket-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Block Public Access (account-level): all 4 settings True
  [✓|✗] Block Public Access (bucket-level): all 4 settings True
  [✓|✗] Default encryption: SSE-S3 | SSE-KMS (<key-arn>)
  [✓|✗] Object Ownership: BucketOwnerEnforced
  [✓|✗] Versioning: Enabled (MFA Delete: Enabled|Disabled)
  [✓|✗] Bucket policy: HTTPS-enforce + SSE-enforce
  [✓|✗] Access logging: Enabled (target: <log-bucket>)
  [✓|✗] CloudTrail data events: Enabled
  [✓|✗] Lifecycle rules: <rule-summary> | None (optional)
  [✓|✗] Replication: CRR→<dest> | SRR→<dest> | None
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

---

### Perfect example output — PREREQUISITES_MISSING

```text
BUCKET: prod-order-data
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Block Public Access (account-level): all 4 settings True
  [✓] Block Public Access (bucket-level): all 4 settings True
  [✗] Default encryption: SSE-KMS selected but KMS key ARN not provided — operator must supply CMK ARN
  [✓] Object Ownership: BucketOwnerEnforced
  [✓] Versioning: Enabled (MFA Delete: Disabled)
  [✓] Bucket policy: HTTPS-enforce + SSE-enforce
  [✗] Access logging: log target bucket s3-access-logs-prod does not exist — create target bucket first
  [✗] CloudTrail data events: trail management-events not found — verify trail name and region
  [OPTIONAL] Lifecycle rules: None (not requested for this workload)
  [✗] Replication: replication IAM role not provided — create role with s3:ReplicateObject + kms:Decrypt
VERIFICATION_COMMANDS:
  aws kms list-aliases --query 'Aliases[?AliasName==`alias/prod-s3-key`]'
  aws s3api head-bucket --bucket s3-access-logs-prod
  aws cloudtrail describe-trails --query 'trailList[?Name==`management-events`]'
  aws iam get-role --role-name s3-replication-role
```
