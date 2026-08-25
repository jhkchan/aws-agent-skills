---
name: cloudtrail-org-trail-auditor
description: Audits AWS CloudTrail organization trails for full-org coverage, multi-region logging, KMS encryption (SSE-KMS) of log delivery, log-file validation (digest integrity), CloudWatch Logs delivery, CloudTrail Insights enablement, and log retention posture. Emits a deterministic verdict (NO_ORG_TRAIL | NO_ENCRYPTION | NO_VALIDATION | NO_INSIGHTS | CONFIG_GAP | OK) per trail with enumerated findings and CLI remediation. Use when reviewing CloudTrail trail configurations, checking org-wide audit coverage, validating log integrity, confirming KMS encryption, verifying CloudTrail Insights, or hardening forensic-readiness posture before compliance assessment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline trail-config classification. Live-account audits use aws cloudtrail describe-trails, get-trail-status, get-insight-selectors, and aws logs describe-log-groups (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  verdict_shape: NO_ORG_TRAIL | NO_ENCRYPTION | NO_VALIDATION | NO_INSIGHTS | CONFIG_GAP | OK
  when_to_use: 'Pre-compliance review of an AWS Organizations CloudTrail trail''s configuration: org-wide coverage, multi-region logging, KMS-encryption, log-file integrity validation, Insights enablement, and log retention posture.'
  when_not_to_use: 'Single-account trail that is NOT part of an AWS Organization (different audit scope)., CloudTrail Lake event-data-store queries (different API surface: list-event-data-stores / start-query)., Configuring data-event selectors for S3/Lambda/DynamoDB resources (separate skill)., Macie, GuardDuty, or Security Hub finding triage (use the dedicated triage skills)., Cost-optimization of CloudTrail ingest volume (use a cost-audit skill).'
  activation_triggers: audit this CloudTrail org trail, is my org trail configured correctly, check CloudTrail org trail log file validation, is the CloudTrail org trail encrypted with KMS, are CloudTrail Insights enabled on the org trail, CloudTrail multi-region check on the org trail, CloudTrail org trail coverage audit, verify CloudTrail forensic readiness for the org
  invocation_schema: "{output: 'Deterministic per-trail block: TRAIL / VERDICT / REASON / FINDINGS / REMEDIATION.\n    VERDICT is one of NO_ORG_TRAIL | NO_ENCRYPTION | NO_VALIDATION | NO_INSIGHTS |\n    CONFIG_GAP | OK (first-fail-wins order).', properties: {cw_retention_days: {description: CloudWatch\n        Logs retentionInDays for the trail's log group., type: integer}, insight_selectors: {\n      description: get-insight-selectors output (optional)., type: array}, trail_config: {\n      description: describe-trails output (JSON or key-value summary) for one trail.,\n      type: object}, trail_name_or_arn: {description: Trail name/ARN for live-account\n        audit (alternative to trail_config)., type: string}, trail_status: {description: get-trail-status\n        output (optional but recommended)., type: object}}, required: [trail_config],\n  type: object}"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudTrail, organization trail, multi-region trail, KMS encryption, log file validation, digest files, CloudWatch Logs, CloudTrail Insights, log retention, audit logging, compliance, forensic readiness, IsOrganizationTrail, IsMultiRegionTrail, LogFileValidationEnabled, trail auditor, API activity logging
  tags: cloudtrail, governance, audit-logging, compliance, security, insights, kms-encryption
---

# CloudTrail Organization Trail Auditor

## Quick start (decision tree — read first)

Evaluate dimensions in order; **the first failing dimension is the verdict.**

| # | Check | Fail verdict | Risk |
|---|---|---|---|
| 1 | `IsOrganizationTrail: false` (from `describe-trails`) | **NO_ORG_TRAIL** | CRITICAL |
| 2 | `KmsKeyId` null/empty (SSE-S3 defaults) | **NO_ENCRYPTION** | CRITICAL |
| 3 | `LogFileValidationEnabled: false` | **NO_VALIDATION** | HIGH |
| 4 | `InsightsSelectors: []` (from `get-insight-selectors`) | **NO_INSIGHTS** | MEDIUM |
| 5 | `IsMultiRegionTrail: false` OR `CloudWatchLogsLogGroupArn: null` OR `IncludeGlobalServiceEvents: false` OR CW retention < 90 days | **CONFIG_GAP** | MEDIUM |
| 6 | All above pass | **OK** | LOW |

**Pre-flight gate (mandatory):** `get-trail-status` returns `IsLogging`. If `false`, append a CRITICAL finding regardless of the verdict, and recommend `start-logging`.

**Invisible dependencies (require extra API calls — surface gaps in FINDINGS, never silently change the verdict):** Organizations trusted-service access for `cloudtrail.amazonaws.com`, S3 bucket-policy `s3:x-amz-acl: bucket-owner-full-control` ACL, KMS key-policy `kms:GenerateDataKey*` grant, S3 lifecycle rules on the log and digest prefixes.

**Output one block per trail:** `TRAIL / VERDICT / REASON / FINDINGS / REMEDIATION` (see Output format).

## Mindset

**One-line takeaway:** the verdict is the **first** failing dimension in a
strict order of severity — org coverage → encryption → validation → insights
→ config-gap. A trail that is not an org trail fails the most fundamental
audit gate regardless of how well everything else is configured.

CloudTrail is the forensic bedrock of an AWS account. A misconfigured org
trail does not merely "miss events"; it creates **silent blind spots** where
attacker actions leave no trace. Step 0 enumerates the non-obvious
CloudTrail behaviors that change classification; Steps 1–6 are the
deterministic first-fail-wins tree.

## Pre-flight: trail status gate (run before classification)

Before evaluating trail configuration, verify the trail is actually logging.
A trail with perfect configuration but `IsLogging: false` collects nothing —
it is the most overlooked audit dimension because `describe-trails` returns the
config without the status.

| Status field | Value | Effect |
|---|---|---|
| `IsLogging` (get-trail-status) | `true` | Proceed with full audit. |
| `IsLogging` (get-trail-status) | `false` | Trail is STOPPED. This is a CRITICAL finding. Append to FINDINGS: "Trail isLogging=false — no events are being recorded despite configuration. Run `aws cloudtrail start-logging --name <trail>`." Continue the config audit so all gaps are surfaced, but note the trail is inactive. |
| Status unknown (no get-trail-status provided) | — | Proceed but append a WARNING: "Trail logging status not provided — verify with `aws cloudtrail get-trail-status --name <trail>`. A trail may be correctly configured but silently stopped." |

**Multi-trail sweep note:** `aws cloudtrail describe-trails` returns all trails
visible to the caller, but an org trail is only visible in the management
account (or delegated administrator). If the input comes from a member account,
the org trail will NOT appear — verify the caller is in the management account
before concluding NO_ORG_TRAIL.

> Malformed-config ERROR block moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.

## Process — Classification logic (apply in order, first-fail wins)

### Step 0: Expert knowledge — non-obvious CloudTrail behaviors

> Step 0 expert knowledge moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

### Step 1: Organization trail check (NO_ORG_TRAIL — CRITICAL)

If `IsOrganizationTrail` is `false` or absent, the trail does NOT cover member
accounts. This is the most fundamental gap — an org without an org trail has
no centralized audit visibility into member-account API activity.

**Verdict: NO_ORG_TRAIL** (CRITICAL risk).

Even if every other dimension (encryption, validation, Insights) is correctly
configured, the trail only logs the account it was created in. Member-account
activity is invisible to the management account's security team.

**Edge case — delegated administrator:** If the trail was created by a
delegated administrator account (not the management account), the trail is
still an org trail — `IsOrganizationTrail: true` applies regardless of which
account created it, as long as the org trusted-service access is active.

### Step 2: KMS encryption check (NO_ENCRYPTION — CRITICAL)

If `IsOrganizationTrail: true` (passed Step 1), check `KmsKeyId`:

- **`KmsKeyId` is null, empty, or absent** → SSE-S3 (Amazon-managed AES-256)
  is the default. This IS encryption, but the key is not customer-controlled.
  For compliance frameworks (SOC 2, HIPAA, FedRAMP) requiring customer-managed
  keys, this is a finding. **Verdict: NO_ENCRYPTION** (CRITICAL risk).

- **`KmsKeyId` is present** → Verify the key is in the same region as the
  trail and that the key policy grants CloudTrail service access. If the key
  policy is missing the CloudTrail service principal, log delivery will fail
  silently — the trail appears active but logs stop appearing in S3. Note as
  a WARNING in FINDINGS but do not fail the dimension.

**Verify the S3 bucket policy, KMS key policy, and S3 lifecycle rules
(all three are invisible from `describe-trails` and silently break member-account
log access on org trails). Run these in order; treat any non-conformance as a
CONFIG_GAP finding:**

```bash
# 1. S3 bucket policy — must allow cloudtrail.amazonaws.com s3:PutObject with
#    Condition StringEquals s3:x-amz-acl == bucket-owner-full-control.
aws s3api get-bucket-policy --bucket <S3BucketName> --query Policy --output text \
  | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'

# 2. KMS key policy — must allow cloudtrail.amazonaws.com kms:GenerateDataKey*
#    and kms:Decrypt with EncryptionContext:aws:cloudtrail:arn == <trail-arn>.
aws kms describe-key --key-id <KmsKeyId> --query 'KeyMetadata.Policy' --output text \
  | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'

# 3. S3 lifecycle rules — must NOT expire the log prefix (<prefix>/) or the
#    digest prefix (<prefix>/CloudTrail-Digest/) before the compliance window.
aws s3api get-bucket-lifecycle-configuration --bucket <S3BucketName> --output json \
  | jq '.Rules[] | select(.Filter.Prefix | test("^<prefix>(CloudTrail-Digest/)?"))'

# 4. CloudWatch Logs retention — must be on the trail's log group, >= 90 days.
aws logs describe-log-groups --log-group-name-prefix <CloudWatchLogsLogGroupArn-prefix> \
  --query 'logGroups[*].[logGroupName,retentionInDays]' --output table
```

### Step 3: Log file validation check (NO_VALIDATION — HIGH)

If Steps 1-2 passed, check `LogFileValidationEnabled`:

- **`LogFileValidationEnabled: false` or absent** → No digest files are
  generated. An attacker with S3 write access can modify, delete, or inject
  log files without detection. **Verdict: NO_VALIDATION** (HIGH risk).

- **`LogFileValidationEnabled: true`** → Digest files are generated.
  Integrity checking is possible via `aws cloudtrail validate-logs`.
  Note: validation detects **offline** tampering (files modified after
  delivery), not real-time tampering during the write window. Still a
  critical detective control for compliance and forensic integrity.

### Step 4: CloudTrail Insights check (NO_INSIGHTS — MEDIUM)

If Steps 1-3 passed, check Insights selectors. The rule is deterministic:

- **No `InsightsSelectors` data provided** → Verdict proceeds to Step 5 (does
  NOT block OK), but the REASON field MUST begin with the literal phrase
  `"Insights unverified"` and FINDINGS MUST include an `[UNVERIFIED]` line:
  "Operator must call `aws cloudtrail get-insight-selectors --trail-name
  <name>` to close this dimension." Do NOT emit `NO_INSIGHTS` without explicit
  evidence (empty list); do NOT emit `OK` without surfacing the gap. The
  fallback is operator-visible, never silent.

- **`InsightsSelectors` is empty (`[]`) or explicitly not configured** → No
  anomaly detection on API call volume or error rates. **Verdict:
  NO_INSIGHTS** (MEDIUM risk).

- **`InsightsSelectors` present with `ApiCallRateInsight` and/or
  `ApiErrorRateInsight`** → Insights is enabled. Note: Insights requires a
  7-day baseline before detecting anomalies — a trail created <7 days ago
  will not produce Insights findings yet, but this is NOT a misconfiguration.

### Step 5: Configuration-gap check (CONFIG_GAP — MEDIUM)

If Steps 1-4 passed, evaluate secondary dimensions. ANY of the following
triggers CONFIG_GAP:

| Sub-check | Condition | Finding |
|---|---|---|
| Multi-region | `IsMultiRegionTrail: false` | Shadow regions — API activity in other regions is invisible. |
| CloudWatch Logs | `CloudWatchLogsLogGroupArn` null/empty | No real-time log streaming — SIEM/CW alarms cannot react to CloudTrail events. |
| Global service events | `IncludeGlobalServiceEvents: false` | IAM, STS, Route 53, CloudFront events dropped. |
| Log retention | CloudWatch Logs `retentionInDays: null` or `< 90` | No compliance boundary (infinite storage or too-short retention for investigation). |
| S3 bucket ACL | Not `bucket-owner-full-control` | Member-account logs unreadable by management account. |

If ANY of these fail, **Verdict: CONFIG_GAP** (MEDIUM risk). Enumerate each
failing sub-check in FINDINGS.

### Step 6: All dimensions pass (OK)

If all dimensions pass (org trail, KMS encryption, validation, Insights,
multi-region, CloudWatch Logs, global events, retention >= 90 days):
**Verdict: OK** (LOW risk).

## Output format (per trail)

```text
TRAIL: <trail-name>
VERDICT: NO_ORG_TRAIL | NO_ENCRYPTION | NO_VALIDATION | NO_INSIGHTS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the first failing dimension and its step>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

### Worked example — org trail with validation disabled

```text
TRAIL: org-trail-no-validation
VERDICT: NO_VALIDATION
REASON: LogFileValidationEnabled is false on an org trail — digest files are
not generated, so log tampering cannot be detected via validate-logs (Step 3).
FINDINGS:
  - [OK] IsOrganizationTrail: true — org coverage active (Step 1)
  - [OK] KmsKeyId configured — SSE-KMS encryption active (Step 2)
  - [HIGH] LogFileValidationEnabled: false — no digest files, tampering
    undetectable (Step 3)
REMEDIATION:
  1. Enable log file validation:
     aws cloudtrail update-trail --name org-trail-no-validation --enable-log-file-validation
  2. Verify digest files appear in S3:
     aws s3 ls s3://<bucket>/CloudTrail-Digest/ --recursive | head -20
```

## Pre-flight safety checks (run before any remediation CLI)

> Pre-flight safety checks moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

## Anti-Patterns — NEVER

- NEVER assume an org trail is multi-region. `IsOrganizationTrail` and
  `IsMultiRegionTrail` are independent flags. An org trail logging only one
  region creates a blind spot for every other region — an attacker can
  operate from `eu-west-1` against a trail in `us-east-1` and leave no trace.

- NEVER treat SSE-S3 (Amazon-managed key) as satisfying a KMS-encryption
  requirement. SSE-S3 IS encryption, but the key is managed by AWS — the
  customer cannot audit key usage, set key policies, or rotate on their own
  schedule. Compliance frameworks requiring customer-managed keys treat null
  `KmsKeyId` as NO_ENCRYPTION regardless of S3 default encryption.

- NEVER classify a trail as OK without verifying `IsLogging: true`. A trail
  with perfect configuration but `IsLogging: false` is collecting nothing.
  `describe-trails` returns the config; `get-trail-status` returns the status.

- NEVER assume CloudTrail Insights works immediately after enablement. It
  requires a minimum 7-day baseline of management events before it can detect
  anomalies.

- NEVER conflate CloudTrail log retention with CloudWatch Logs retention.
  CloudTrail itself has no retention setting — logs persist in S3 until a
  lifecycle policy removes them. CloudWatch Logs retention is a separate
  property on the log group (`retentionInDays`).

- NEVER overlook the S3 bucket policy for org trails. The bucket must grant
  `cloudtrail.amazonaws.com` `s3:PutObject` with condition
  `s3:x-amz-acl: bucket-owner-full-control`. Without the ACL condition,
  member-account logs are owned by the member account and the management
  account cannot read them.

- NEVER assume `IncludeGlobalServiceEvents: true` is the default in all
  tooling. Terraform and CloudFormation templates sometimes omit this field;
  the default varies by SDK version. Explicitly verify it is `true`.

- NEVER recommend `delete-trail` to remediate any configuration gap.
  `delete-trail` is irreversible, drops the trail name and S3 prefix
  continuity, breaks downstream EventBridge rules and CloudWatch alarms keyed
  to the trail ARN, and creates a forensic gap until a replacement trail
  begins delivery. Always use `update-trail` (in-place modification); it
  preserves the ARN, S3 prefix, and all downstream integrations. If a
  deletion is genuinely required (e.g., trail-name conflict), require a
  second operator confirmation and capture a backup first.

- NEVER ignore the KMS key policy when auditing CloudTrail KMS encryption.
  A `KmsKeyId` set on the trail with a missing or restrictive key policy
  causes silent log-delivery failure — the trail is "encrypted" but nothing
  is being written.

- NEVER classify NO_INSIGHTS if the insight-selector data was not provided.
  Surface the gap as `[UNVERIFIED]` per Step 4 — do not guess.

- NEVER rely on a default S3 lifecycle configuration (e.g., a bucket-wide
  `ExpirationInDays` shipped by a CDK construct or Terraform module) as the
  CloudTrail retention control. S3 lifecycle expires objects silently — no
  notification, no digest-chain check, no object lock. A common compliance
  failure: the default rule deletes raw log files after 30/60/90 days while
  digests remain, so `validate-logs` reports a green chain pointing at
  missing files and the audit trail silently shortens. Always inspect
  `aws s3api get-bucket-lifecycle-configuration` and surface any
  non-versioned expiry on the log or digest prefix as CONFIG_GAP. Prefer S3
  Object Lock + Glacier Deep Archive for compliance retention over lifecycle
  expiry.

- NEVER assume a single-region trail is sufficient for an org, even if all
  workloads are in one region. AWS global services (IAM, STS, Route 53) and
  cross-region API calls (e.g., a Lambda in us-east-1 assuming a role in
  eu-west-1) generate events in the source region.

## Remediation guidance

### For NO_ORG_TRAIL

1. Verify the caller is in the management account:
   `aws organizations describe-organization --profile <p>`
2. Enable CloudTrail as a trusted service in Organizations:
   `aws organizations enable-aws-service-access --service-principal cloudtrail.amazonaws.com`
3. Create or update the trail to be an org trail:
   `aws cloudtrail update-trail --name <trail> --is-organization-trail`
4. Verify the S3 bucket policy allows writes from all member accounts (see
   NEVER list — bucket-owner-full-control condition).

### For NO_ENCRYPTION

1. Identify or create a KMS key in the trail's region:
   `aws kms create-key --description "CloudTrail SSE-KMS key" --profile <p>`
2. Attach a key policy granting CloudTrail service access:
   ```json
   {"Statement": [{"Effect": "Allow", "Principal":
   {"Service": "cloudtrail.amazonaws.com"}, "Action":
   ["kms:GenerateDataKey*", "kms:Decrypt"], "Resource": "*",
   "Condition": {"StringEquals": {"kms:CallerAccount": "<account>",
   "kms:EncryptionContext:aws:cloudtrail:arn":
   "arn:aws:cloudtrail:<region>:<account>:trail/<name>"}}}]}
   ```
3. Update the trail:
   `aws cloudtrail update-trail --name <trail> --kms-key-id <key-id>`
4. Verify log delivery continues:
   `aws cloudtrail get-trail-status --name <trail>`

### For NO_VALIDATION

1. Enable log file validation:
   `aws cloudtrail update-trail --name <trail> --enable-log-file-validation`
2. Verify digest files appear:
   `aws s3 ls s3://<bucket>/<prefix>/CloudTrail-Digest/ --recursive | head -20`
3. Schedule periodic validation:
   `aws cloudtrail validate-logs --trail-name <trail> --start-time <ts> --end-time <ts>`

### For NO_INSIGHTS

1. Enable Insights selectors:
   `aws cloudtrail put-insight-selectors --trail-name <trail>
   --insight-selectors '[{"InsightType": "ApiCallRateInsight"},
   {"InsightType": "ApiErrorRateInsight"}]'`
2. Note: Insights requires 7 days of baseline data before producing findings.
3. Monitor cost — Insights is billed per management event analyzed.

### For CONFIG_GAP

- **Single-region trail:** `aws cloudtrail update-trail --name <trail>
  --is-multi-region-trail`
- **No CloudWatch Logs:** Create a log group and IAM role, then update:
  `aws cloudtrail update-trail --name <trail>
  --cloudwatch-logs-log-group-arn <arn> --cloudwatch-logs-role-arn <arn>`
- **Global service events disabled:** `aws cloudtrail update-trail --name
  <trail> --include-global-service-events`
- **Short/missing retention:** `aws logs put-retention-policy
  --log-group-name <group> --retention-in-days 365`

### For OK

1. No remediation required.
2. Recommend periodic `validate-logs` runs (weekly digest verification).
3. Recommend testing org-trail member-account visibility quarterly.

## Reference — CloudTrail internals (deep material)

> CloudTrail internals deep material moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Recent AWS features (2024-2026)

> Recent AWS features moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge (non-obvious CloudTrail behaviors), CloudTrail internals deep material, recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks — confirmation gate, rollback capture, Insights cost, org-trail enablement check
- [references/error-handling.md](references/error-handling.md) — malformed trail-configuration ERROR output block

## Domain

AWS CloudOps / CloudTrail Governance, Compliance & Forensic Readiness.

## AWS documentation

- **AWS CloudTrail User Guide** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html
- **CloudTrail Security** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/security.html
- **CloudTrail API Reference** — https://docs.aws.amazon.com/awscloudtrail/latest/APIReference/
- **CloudTrail CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudtrail/
- **CloudTrail Lake** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html
