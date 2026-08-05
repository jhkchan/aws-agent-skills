# End-to-end usage scenario: cloudwatch-logs-retention-auditor

A walkthrough showing the skill auditing a CloudWatch Logs log group
that fails the COST_RISK dimension: long retention × high volume with a
CMK associated. Demonstrates first-fail-wins ordering (Step 1 and 2
pass, Step 3 fires), the `storedBytes` vs current-storage distinction,
and the cost-aware remediation workflow.

## Input (user prompt)

> Audit this CloudWatch Logs group before we onboard the payments
> service. We're seeing higher-than-expected AWS bill and suspect log
> retention.

```json
{
  "logGroupName": "/prod/checkout-api",
  "arn": "arn:aws:logs:us-east-1:111111111111:log-group:/prod/checkout-api:*",
  "creationTime": 1580000000000,
  "retentionInDays": 3650,
  "kmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/cmk-prod-logs",
  "storedBytes": 549755813888
}
```

Metric filters: 1 (filterName: ErrorCount, filterPattern: "ERROR")
Subscription filters: 1 (destinationArn: arn:aws:lambda:us-east-1:111111111111:function:log-shipper, filterPattern: "")
Anomaly detectors: 0

## Skill output

```text
LOG_GROUP: /prod/checkout-api
VERDICT: COST_RISK
REASON: retentionInDays=3650 (10-year cap) on a group with storedBytes
~512 GB crosses the COST_RISK threshold (Step 3). Retention (Step 1) and
CMK encryption (Step 2) pass first-fail-wins; COST_RISK fires at Step 3
because retention × volume is materially cost-excessive. Anomaly coverage
also missing (would be CONFIG_GAP if cost profile were acceptable).
FINDINGS:
  - [HIGH] retentionInDays=3650 with storedBytes=549755813888 (~512 GB)
    exceeds the COST_RISK threshold (retention >= 3653 OR (>=731 AND
    storedBytes >= 10 GB)) (Step 3). Estimated daily ingestion ~450 MB;
    estimated current storage ~164 GB; projected storage cost material.
  - [HIGH] Lambda subscription filter "log-shipper" on a high-volume
    group — Lambda invocation cost on this volume frequently exceeds
    the CloudWatch Logs storage charge. filterPattern is empty (""),
    matching every event (additive cost multiplier).
  - [MEDIUM] No CloudWatch Logs Anomaly Detector — unknown-unknowns
    (error spikes, latency shifts) invisible (Step 4, suppressed by
    first-fail-wins but reported).
  - [OK] retentionInDays is present (Step 1 passes — not Never expire).
  - [OK] kmsKeyId is present with an in-region CMK (Step 2 passes —
    SSE-KMS CMK associated, auditable via CloudTrail kms:Decrypt events).
REMEDIATION:
  1. Shorten retention to the minimum compliance window. If 365 days
     satisfies your SOC 2 / ISO 27001 requirement:
     aws logs put-retention-policy --log-group-name /prod/checkout-api
       --retention-in-days 365 --profile default
     Note: existing events expire on their original schedule, not
     immediately — plan cleansing separately.
  2. Tighten the Lambda subscription filter's filterPattern from "" to
     a meaningful pattern (e.g., "ERROR") to reduce invocation volume,
     OR replace synchronous Lambda fan-out with Kinesis Data Streams +
     enhanced fan-out, OR move the consumer to a scheduled Logs Insights
     query on a data subset.
  3. Add a CloudWatch Logs Anomaly Detector:
     aws logs put-anomaly-detector
       --log-group-arn-list arn:aws:logs:us-east-1:111111111111:log-group:/prod/checkout-api:*
       --detector-name checkout-api-anomaly --eval-frequency FIVE_MIN
     Wait 14 days for baseline training before relying on findings.
  4. Add a CloudWatch alarm on IncomingBytes to catch future ingestion
     surges before they recur:
     aws cloudwatch put-metric-alarm --alarm-name checkout-ingestion-spike
       --metric-name IncomingBytes --namespace AWS/Logs
       --statistic Sum --period 300 --threshold 5368709120
       --comparison-operator GreaterThanThreshold --evaluation-periods 1
       --dimensions Name=LogGroupName,Value=/prod/checkout-api
  5. If 3650-day retention is genuinely required by a compliance
     regulator, document the decision and archive cold logs to S3
     (with S3 lifecycle to Glacier) via a Firehose delivery stream,
     then shorten the CloudWatch Logs retention to 90 days for the
     queryable hot tier.
```

## What the skill caught that a generic assistant misses

1. **First-fail-wins ordering.** A generic assistant says "retention is
   too long" and might also note "no anomaly detector." The skill
   emits a single deterministic VERDICT (COST_RISK) per the ordered
   matrix — the operator triages one verdict, not a list of issues.
   The lower-priority anomaly gap is still enumerated in FINDINGS but
   cannot muddy the verdict.

2. **`storedBytes` vs current storage distinction.** A generic
   assistant reads `storedBytes: 549 GB` and treats it as current
   storage. The skill explains that `storedBytes` is cumulative since
   creation (~5 years ago at this snapshot), divides by age-in-days
   to estimate daily ingestion, and multiplies by current retention
   to estimate actual current storage — yielding ~164 GB rather than
   549 GB. This is the difference between over- and under-estimating
   the cost fix by 3x.

3. **Lambda subscription filter as cost multiplier.** A generic
   assistant treats the subscription filter as "fine" or "configured."
   The skill identifies the empty `filterPattern: ""` as a no-op that
   matches every event, multiplying Lambda invocations unnecessarily
   — frequently the dominant cost driver on high-volume groups.

4. **The "retention changes apply only to new events" caveat.** A
   generic assistant says "shorten retention to fix cost." The skill
   warns that existing events expire on their original schedule, so
   the cost fix is gradual — for immediate cleansing, a separate
   destructive operation is required.

5. **KMS-request cost trade-off when CMK is already present.** A
   generic assistant might recommend CMK as a security improvement.
   The skill recognises the CMK is already present, projects the
   KMS-request cost impact at high scale, and does NOT recommend
   a redundant or more-expensive CMK change.

## Slash-command invocation

```
/aws:audit-cloudwatch-logs-retention
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this CloudWatch Logs group before we onboard payments"
```

The orchestrator emits
`[Phase: Audit | Skills routed: cloudwatch-logs-retention-auditor]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this CloudWatch Logs group"
# [Phase: Audit | Skills routed: cloudwatch-logs-retention-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the retention, validate the log group posture:

```bash
# Verify retention was applied
aws logs describe-log-groups --log-group-name-prefix /prod/checkout-api \
  --profile default --query 'logGroups[0].retentionInDays'

# Confirm the CMK is still associated and the key is Enabled
aws logs describe-log-groups --log-group-name-prefix /prod/checkout-api \
  --profile default --query 'logGroups[0].kmsKeyId'
aws kms describe-key --key-id cmk-prod-logs --profile default \
  --query 'KeyMetadata.KeyState'

# Confirm the anomaly detector exists and is ACTIVE (not TRAINING)
aws logs describe-anomaly-detectors \
  --log-group-arn-list arn:aws:logs:us-east-1:111111111111:log-group:/prod/checkout-api:* \
  --profile default
```

Then monitor CloudWatch Logs `IncomingBytes` for 1-2 weeks to confirm
the ingestion alarm fires before cost surprises recur.
