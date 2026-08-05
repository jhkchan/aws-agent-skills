# End-to-end usage scenario: cloudtrail-org-trail-auditor

A walkthrough showing the skill auditing an organization trail that has
KMS encryption but log file validation disabled and no CloudTrail Insights,
demonstrating first-fail-wins verdict ordering, per-dimension findings, and
CLI remediation.

## Input (user prompt)

> Review this CloudTrail trail before our SOC 2 compliance assessment next
> week. Need to make sure our org-wide audit logging is solid.

```text
Trail name: prod-org-audit-trail
Trail ARN: arn:aws:cloudtrail:us-east-1:111111111111:trail/prod-org-audit-trail
S3BucketName: prod-cloudtrail-logs-111111111111

Trail configuration (describe-trails):
  IsOrganizationTrail: true
  IsMultiRegionTrail: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/prod-trail-kms
  LogFileValidationEnabled: false
  IncludeGlobalServiceEvents: true
  CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:prod-ct-cw:*
  CloudWatchLogsRoleArn: arn:aws:iam::111111111111:role/CloudTrail-CW-prod

Trail status (get-trail-status):
  IsLogging: true

Insights selectors (get-insight-selectors):
  (empty — no selectors configured)

CloudWatch Logs log-group retention: 90 days
```

## Skill output

```text
TRAIL: prod-org-audit-trail
VERDICT: NO_VALIDATION
REASON: LogFileValidationEnabled is false on an org trail — digest files are
not generated, so log tampering cannot be detected via validate-logs (Step 3).
Insights is also not configured.
FINDINGS:
  - [OK] IsOrganizationTrail: true — org coverage active (Step 1)
  - [OK] KmsKeyId configured (prod-trail-kms) — SSE-KMS encryption active (Step 2)
  - [HIGH] LogFileValidationEnabled: false — no digest files, tampering
    undetectable, SOC 2 integrity-control gap (Step 3)
  - [MEDIUM] No Insights selectors configured — no anomaly detection on API
    call volume or error rates (Step 4)
  - [OK] IsMultiRegionTrail: true — all regions covered (Step 5)
  - [OK] CloudWatch Logs delivery configured — SIEM streaming active (Step 5)
  - [OK] IncludeGlobalServiceEvents: true — IAM/STS events captured (Step 5)
  - [OK] CloudWatch Logs retention: 90 days (Step 5)
REMEDIATION:
  1. Enable log file validation (highest priority for SOC 2):
     aws cloudtrail update-trail --name prod-org-audit-trail --enable-log-file-validation
  2. Verify digest files appear in S3 within 1 hour:
     aws s3 ls s3://prod-cloudtrail-logs-111111111111/CloudTrail-Digest/ --recursive | head -20
  3. Enable CloudTrail Insights (note: metered per management event analyzed):
     aws cloudtrail put-insight-selectors --trail-name prod-org-audit-trail \
       --insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'
  4. Back up current trail config before changes:
     aws cloudtrail describe-trails --trail-name-list prod-org-audit-trail \
       --output json > /tmp/prod-org-audit-trail-backup.json
```

## What the skill caught that a generic assistant misses

1. **First-fail-wins verdict ordering.** A generic assistant lists "validation
   is off" alongside "Insights is missing" without prioritization. The skill
   classifies NO_VALIDATION as the verdict (Step 3 fails before Step 4) and
   surfaces Insights as a secondary finding — the operator fixes the
   compliance-critical gap first.

2. **SSE-KMS vs SSE-S3 distinction.** The trail has a KmsKeyId, so the skill
   confirms SSE-KMS is active (Step 2 passes). A naive auditor that only
   checks "is encryption on" would miss the customer-managed-key requirement
   entirely.

3. **Validation is a tampering tripwire, not prevention.** The skill explains
   that digest files detect offline tampering (file modified after delivery)
   but cannot block real-time modification — setting the right compliance
   expectation for the SOC 2 assessor.

4. **Insights billing awareness.** The remediation notes that enabling
   Insights starts a metered billing dimension. A generic assistant just
   says "enable Insights" without surfacing the cost implication.

## Slash-command invocation

```
/aws:audit-cloudtrail-org-trail
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our CloudTrail org trail before the SOC 2 assessment"
```

The orchestrator emits
`[Phase: Audit | Skills routed: cloudtrail-org-trail-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the trail, validate the posture:

```bash
# Verify log file validation is now enabled
aws cloudtrail describe-trails --trail-name-list prod-org-audit-trail \
  --profile default --output json | jq '.trailList[0].LogFileValidationEnabled'

# Confirm Insights selectors are active
aws cloudtrail get-insight-selectors --trail-name prod-org-audit-trail \
  --profile default

# Run a periodic digest validation (weekly recommended)
aws cloudtrail validate-logs --trail-name prod-org-audit-trail \
  --start-time 2026-07-29T00:00:00Z --end-time 2026-08-05T00:00:00Z \
  --profile default

# Verify Organizations trusted-service access is active (silent-failure check)
aws organizations list-aws-service-access-for-organization \
  --profile default | jq '.EnabledServicePrincipals[] | select(.ServicePrincipal=="cloudtrail.amazonaws.com")'
```
