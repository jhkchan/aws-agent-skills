# Diagnostic Commands

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Remediation guidance (moved from SKILL.md)

### For PUBLIC_BUS — wildcard or cross-account event injection (Steps 5a-5c)

1. Replace `Principal: "*"` with specific account/role ARNs. If
   cross-account PutEvents is required, use `aws:PrincipalOrgID` or
   `aws:SourceAccount` conditions:
   ```bash
   aws events put-permission --event-bus-name <bus> \
     --action events:PutEvents \
     --principal arn:aws:iam::222222222222:role/app-publisher \
     --statement-id CrossAccountScoped \
     --condition '{"Type":"StringEquals","Key":"aws:SourceAccount","Value":"222222222222"}'
   ```
2. Remove the wildcard statement:
   ```bash
   aws events remove-permission --event-bus-name <bus> --statement-id OpenIngest
   ```
3. Assume breach — audit CloudTrail for `events:PutEvents` from
   unexpected principals. Check downstream targets for anomalous
   invocations triggered by injected events.

### For NO_DLQ — missing dead-letter queue (Step 6)

1. Create a dedicated SQS DLQ:
   ```bash
   aws sqs create-queue --queue-name <bus>-dlq
   ```
2. Attach to each target via `put-targets` with `DeadLetterConfig`:
   ```bash
   aws events put-targets --rule <rule> --event-bus-name <bus> \
     --targets '[{"Id":"<target-id>","Arn":"<target-arn>","DeadLetterConfig":{"Arn":"arn:aws:sqs:<region>:<acct>:<bus>-dlq"}}]'
   ```
3. Set an alarm on DLQ depth (ApproximateNumberOfMessagesVisible > 0).

### For NO_ENCRYPTION — no customer-managed KMS key (Step 7)

1. Associate a CMK:
   ```bash
   aws events update-event-bus --name <bus> \
     --kms-key-identifier arn:aws:kms:<region>:<account>:key/<key-id>
   ```
2. Verify the key policy allows `events.amazonaws.com` service principal
   with `kms:Decrypt` and `kms:GenerateDataKey*`.
3. Enable rotation on the CMK and audit the key policy (route to
   kms-key-policy-auditor).

### For CONFIG_GAP — missing archive or schema discovery (Step 8)

1. Create an archive for replay capability:
   ```bash
   aws events create-archive --archive-name <bus>-archive \
     --event-source-name <bus> --event-pattern '{"replay-name":"*"}' \
     --retention 30
   ```
2. Enable schema discovery:
   ```bash
   aws schemas create-registry --registry-name <bus>-schemas \
     --description "Auto-discovered schemas for <bus>"
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit when rules or targets are added.
3. Verify DLQ alarms are wired to an operational response channel.
