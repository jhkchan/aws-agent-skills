# Error Handling — Backup Audit Automator

## Error handling

### Reports not delivered to S3
- S3 bucket policy is missing or incorrect. Verify
  `backup.amazonaws.com` has `s3:PutObject` permission on the report
  prefix. Re-deliver by triggering a new report job.

### Vault Lock cannot be changed
- The vault is in compliance mode. Compliance mode is permanent and
  cannot be reversed. This is by design. Create a new vault if a
  different configuration is needed.

### Compliance report shows resources without coverage
- These resources are not in any backup plan. Create backup selections
  that include these resources, or tag them for inclusion in existing
  plans.

### Recovery points without KMS encryption
- The backup plan does not specify a KMS key. Update the backup plan
  to include a KMS key in the advanced backup settings. New recovery
  points will be encrypted. Existing unencrypted recovery points remain
  unencrypted until they expire.

### SNS alerts not received
- SNS subscription is not confirmed. Check subscription status and
  confirm the email/HTTPS endpoint. Verify the EventBridge rule is
  enabled and targets the SNS topic.
