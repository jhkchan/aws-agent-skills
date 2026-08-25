# Diagnostic Commands — OpenSearch Snapshot Troubleshooter
Diagnostic and pre-flight command listings, moved verbatim from SKILL.md.

## Pre-flight: domain state and gather-info gate
Gather the canonical configuration and short-circuit on domain
states that mimic snapshot failures. Misclassifying these produces
hours of snapshot debugging for a problem that is not a snapshot
problem.

```bash
# 1. Domain configuration (EngineVersion, ClusterConfig, EBSOptions,
#    SnapshotOptions, LogPublishingOptions, WarmEnabled,
#    ColdStorageOptions, ChangeProgressDetails)
aws opensearch describe-domain --domain-name <domain> --output json
aws opensearch describe-domain-config --domain-name <domain> --output json

ENDPOINT=$(aws opensearch describe-domain --domain-name <domain> \
  --query 'Domain.Endpoint' --output text)

# 2. Recent application logs (snapshot / restore / migration events)
aws logs filter-log-events \
  --log-group-name /aws/opensearch/domains/<domain>/application-logs \
  --start-time $(date -d '-60 minutes' +%s)000 \
  --filter-pattern '"repository_verification_exception" OR "SnapshotException" OR "ConcurrentSnapshotExecutionException" OR "migration_failed" OR "version_not_supported"' \
  --output json

# 3. Repository + snapshot status
curl -sS "https://$ENDPOINT/_cat/repositories?v"
curl -sS "https://$ENDPOINT/_snapshot/_status" | jq '.snapshots[] | {repository, snapshot, state}'

# 4. S3 bucket policy + lifecycle for the snapshot bucket
aws s3api get-bucket-policy --bucket <bucket> --output json 2>/dev/null || echo "No bucket policy"
aws s3api get-bucket-lifecycle-configuration --bucket <bucket> --output json

# 5. Snapshot role trust + simulated permissions
aws iam get-role --role-name <role-name> --query 'Role.AssumeRolePolicyDocument' --output json
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::<account>:role/<role>" \
  --action-names s3:PutObject s3:ListBucket s3:GetObject s3:DeleteObject s3:GetBucketLocation \
  --resource-arns "arn:aws:s3:::<bucket>" "arn:aws:s3:::<bucket>/*" --output json

# 6. CloudWatch automated-snapshot-failure metric
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name AutomatedSnapshotFailure \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 day' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 7. AWS Health (regional OpenSearch events, scheduled maintenance)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING --region us-east-1 --output json
```

## Pre-flight safety checks (run before any state-changing CLI)
- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`PUT _snapshot`, `DELETE _snapshot/<repo>`,
  `_snapshot/<repo>/<snap>/_restore`, `update-domain-config`,
  `s3api put-bucket-lifecycle-configuration`), emit and await
  operator approval. Do NOT execute the CLI or curl until confirmed.
- **Read-only first.** Every probe in the diagnostic tree is
  read-only. Do not perform state-changing operations as diagnostic
  probes.
- **`DELETE _snapshot/<repo>/<snap>`** removes the snapshot from the
  repository; it does NOT delete S3 blobs (segments are deduplicated).
  Confirm before deleting.
- **`_restore`** opens snapshot indices on the target. If a same-named
  index exists, restore skips or fails. Confirm target state first.
- **`update-domain-config` to enable warm/cold** triggers a blue/green
  deployment. Plan outside traffic peaks.
- **`s3api put-bucket-lifecycle-configuration`** overwrites the
  existing lifecycle. Always read current config first and merge.
- **Re-registering a repository** overwrites prior settings. If the
  prior repository had snapshots, the new registration must point at
  the same bucket + prefix or those snapshots become orphaned.
- **Bulk remediation batch limit.** Batch groups of at most 5
  repositories, one CONFIRM per batch.
