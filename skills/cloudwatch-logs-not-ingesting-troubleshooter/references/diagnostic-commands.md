# Diagnostic Commands (load on demand) — CloudWatch Logs Not-Ingesting Troubleshooter

Pre-flight commands, per-layer probe commands, and pre-flight safety checks moved verbatim from SKILL.md. Loaded on demand.

---

## Account-wide pre-flight commands (moved from SKILL.md)

```bash
# 1. Log group configuration (retention, kmsKeyId, dataProtectionPolicy)
aws logs describe-log-groups --log-group-name-prefix <prefix> --output json

# 2. Latest log streams (is anything arriving?)
aws logs describe-log-streams --log-group-name <group> \
  --order-by LastEventTime --descending --limit 5 --output json

# 3. Recent ingested events (if any)
aws logs get-log-events --log-group-name <group> \
  --log-stream-name <stream> --limit 10 --output json

# 4. Subscription filters (fan-out that consumes Lambda concurrency)
aws logs describe-subscription-filters --log-group-name <group> --output json

# 5. Metric filters (pattern may not match the application log format)
aws logs describe-metric-filters --log-group-name <group> --output json

# 6. Data protection policy (account-level content blocking)
aws logs get-data-protection-policy --log-group-name <group> --output json 2>/dev/null || \
  echo "No data protection policy"

# 7. AWS Health (regional CloudWatch Logs events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```
---

## Step 2 — LOG_GROUP_NAMING probes (moved from SKILL.md)

```bash
aws logs describe-log-groups --log-group-name-prefix <expected-prefix> --output json
aws logs describe-log-streams --log-group-name <group> \
  --order-by LastEventTime --descending --limit 5 --output json
```
---

## Step 3 — IAM_PERMISSIONS probe (moved from SKILL.md)

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <emitter-arn> \
  --action-names logs:CreateLogGroup logs:CreateLogStream \
                logs:PutLogEvents logs:DescribeLogStreams \
  --resource-arns arn:aws:logs:<region>:<account>:log-group:<group>:* \
  --output json --profile <p>
```
---

## Step 4 — SEQUENCE_TOKEN probe (moved from SKILL.md)

```bash
aws logs describe-log-streams --log-group-name <group> \
  --log-stream-name-prefix <stream> --output json | \
  jq '.logStreams[0] | {logStreamName, uploadSequenceToken}'
```
---

## Step 5 — AGENT_MISCONFIG probes (moved from SKILL.md)

```bash
# Agent status
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a status 2>/dev/null || \
  systemctl status amazon-cloudwatch-agent 2>/dev/null

# Agent configuration
cat /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json | jq .logs
```
---

## Step 6 — VPC_FLOW_LOGS_DELIVERY probe (moved from SKILL.md)

```bash
aws ec2 describe-flow-logs --filter Name=log-group-name,Values=<group> \
  --output json --profile <p>
```
---

## Step 7 — LAMBDA_AUTO_CREATE probes (moved from SKILL.md)

```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.Role'

aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names logs:CreateLogGroup logs:CreateLogStream logs:PutLogEvents \
  --resource-arns "arn:aws:logs:<region>:<account>:log-group:*" \
  --output json --profile <p>
```
---

## Step 8 — RETENTION_EXPIRED probe (moved from SKILL.md)

```bash
aws logs describe-log-groups --log-group-name-prefix <group> --output json | \
  jq '.logGroups[0].retentionInDays'
```
---

## Step 9 — SUBSCRIPTION_FILTER_CAPACITY probes (moved from SKILL.md)

```bash
aws logs describe-subscription-filters --log-group-name <group> --output json

# Lambda concurrency utilisation for the destination
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<dest-function> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json

aws lambda get-account-settings --output json | jq '.AccountLimit.ConcurrentExecutions'
```
---

## Step 10 — METRIC_FILTER_PATTERN probes (moved from SKILL.md)

```bash
aws logs describe-metric-filters --log-group-name <group> --output json | \
  jq '.metricFilters[] | {filterName, filterPattern, metricTransformations}'

# Test the pattern against actual log events
aws logs filter-log-events --log-group-name <group> \
  --filter-pattern '<pattern>' \
  --start-time $(date -d '-1 hour' +%s)000 --output json | jq '.events | length'
```
---

## Step 11 — DATA_PROTECTION_BLOCKING probe (moved from SKILL.md)

```bash
aws logs get-data-protection-policy --log-group-name <group> --output json --profile <p>
```
---

## Step 12 — CROSS_ACCOUNT_POLICY probes (moved from SKILL.md)

```bash
# Destination side: is there a destination resource policy?
aws logs describe-resource-policies --output json --profile <dest-profile>

# Or for put-destination (cross-account delivery via destination):
aws logs describe-destinations --output json --profile <dest-profile>
```
---

## Pre-flight safety checks (run before any state-changing CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-retention-policy`, `put-subscription-filter`,
  `delete-subscription-filter`, `put-data-protection-policy`,
  `put-resource-policy`, `put-destination-policy`, `associate-kms-key`),
  emit and await operator approval.
- **Read-only first.** Every probe is read-only (`describe-*`, `get-*`,
  `simulate-principal-policy`, `lookup-events`). Do not perform
  state-changing operations as diagnostic probes.
- **`put-retention-policy`** is reversible but lowering the retention
  permanently deletes streams older than the new window. Always raise
  first, never lower, without explicit confirmation.
- **`put-subscription-filter`** replaces the filter for the
  destination; a wrong filter silently drops batches. Test with
  `filter-log-events` first.
- **`put-resource-policy`** changes who can write to the log group.
  A too-broad principal leaks logs to unintended accounts.
- **`associate-kms-key`** re-encrypts with the new key; existing
  events remain under the prior key until expiry. Verify readers have
  `kms:Decrypt` on the new key before switching.
- **Bulk remediation batch limit.** Batch into groups of at most 5 log
  groups, emit a single CONFIRM per batch, and verify between batches.
