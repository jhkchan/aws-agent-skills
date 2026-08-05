---
name: cloudtrail-org-trail-auditor
description: >-
  Audits AWS CloudTrail organization trails for full-org coverage, multi-region
  logging, KMS encryption (SSE-KMS) of log delivery, log-file validation (digest
  integrity), CloudWatch Logs delivery, CloudTrail Insights enablement, and log
  retention posture. Emits a deterministic verdict
  (NO_ORG_TRAIL | NO_ENCRYPTION | NO_VALIDATION | NO_INSIGHTS | CONFIG_GAP | OK)
  per trail with enumerated findings and CLI remediation. Use when reviewing
  CloudTrail trail configurations, checking org-wide audit coverage, validating
  log integrity, confirming KMS encryption, verifying CloudTrail Insights, or
  hardening forensic-readiness posture before compliance assessment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline trail-config classification.
  Live-account audits use aws cloudtrail describe-trails, get-trail-status,
  get-insight-selectors, and aws logs describe-log-groups (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - CloudTrail
  - organization trail
  - multi-region trail
  - KMS encryption
  - log file validation
  - digest files
  - CloudWatch Logs
  - CloudTrail Insights
  - log retention
  - audit logging
  - compliance
  - forensic readiness
  - IsOrganizationTrail
  - IsMultiRegionTrail
  - LogFileValidationEnabled
  - trail auditor
  - API activity logging
tags: [cloudtrail, governance, audit-logging, compliance, security, insights, kms-encryption]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Governance
  verdict_shape: "NO_ORG_TRAIL | NO_ENCRYPTION | NO_VALIDATION | NO_INSIGHTS | CONFIG_GAP | OK"
  when_to_use: >-
    Pre-compliance review of CloudTrail trail configuration, org-wide audit
    coverage checks, log-file integrity validation, KMS-encryption
    verification, CloudTrail Insights enablement checks, or forensic-readiness
    posture audits across an AWS Organization.
  activation_triggers:
    - "audit this CloudTrail trail"
    - "is my org trail configured correctly"
    - "check CloudTrail log file validation"
    - "is CloudTrail encrypted with KMS"
    - "are CloudTrail Insights enabled"
    - "CloudTrail multi-region check"
    - "CloudTrail org trail coverage"
    - "verify CloudTrail forensic readiness"
  invocation_schema:
    type: object
    required: [trail_config]
    properties:
      trail_config:
        type: object
        description: >-
          describe-trails output (JSON or key-value summary) for one trail.
      trail_status:
        type: object
        description: get-trail-status output (optional but recommended).
      insight_selectors:
        type: array
        description: get-insight-selectors output (optional).
      cw_retention_days:
        type: integer
        description: CloudWatch Logs retentionInDays for the trail's log group.
      trail_name_or_arn:
        type: string
        description: Trail name/ARN for live-account audit (alternative to trail_config).
    output: >-
      Deterministic per-trail block: TRAIL / VERDICT / REASON / FINDINGS /
      REMEDIATION. VERDICT is one of NO_ORG_TRAIL | NO_ENCRYPTION |
      NO_VALIDATION | NO_INSIGHTS | CONFIG_GAP | OK (first-fail-wins order).
---

# CloudTrail Organization Trail Auditor

## Mindset

**One-line takeaway:** the verdict is the **first** failing dimension in a
strict order of severity — org coverage is checked before encryption,
encryption before validation, validation before insights, insights before
config-gap. A trail that is not an org trail fails the most fundamental audit
gate regardless of how well everything else is configured.

CloudTrail is the forensic bedrock of an AWS account. Every security
investigation — breach timeline, insider-threat attribution, compliance audit,
configuration drift — starts with CloudTrail logs. An org trail that is
misconfigured does not merely "miss events"; it creates **silent blind spots**
where an attacker's actions leave no trace.

The rest of this skill supplies the depth: Step 0 enumerates the non-obvious
CloudTrail behaviors that change classification; Steps 1-6 are the deterministic
first-fail-wins decision tree. Skim the matrix below, then jump to Step 0.

## Quick reference — verdict matrix

| Dimension checked | Fail verdict | Risk level | Step |
|---|---|---|---|
| `IsOrganizationTrail: false` or absent | **NO_ORG_TRAIL** | CRITICAL | 1 |
| `KmsKeyId` null / empty / SSE-S3 only | **NO_ENCRYPTION** | CRITICAL | 2 |
| `LogFileValidationEnabled: false` | **NO_VALIDATION** | HIGH | 3 |
| No Insights selectors or empty list | **NO_INSIGHTS** | MEDIUM | 4 |
| Multi-region off, no CloudWatch Logs, no global events, no/short retention | **CONFIG_GAP** | MEDIUM | 5 |
| All dimensions pass | **OK** | LOW | 6 |

The verdict is the **first failing dimension** in the order above. A trail
that fails org-trail AND encryption emits `NO_ORG_TRAIL` (the more fundamental
gap), with the encryption finding listed in FINDINGS.

> **Pre-flight critical:** four requirements are invisible to
> `describe-trails` and cause silent failures on org trails — Organizations
> trusted-service access for `cloudtrail.amazonaws.com`, the
> `bucket-owner-full-control` S3 ACL condition, the KMS key policy
> `kms:GenerateDataKey*` grant with the trail-ARN context, and S3 lifecycle
> rules that expire the log or digest prefix. Deep-dive on each is in Step 0.

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

If the trail configuration is malformed (missing `Name`, no `S3BucketName`,
or unparseable JSON), output:

```text
TRAIL: <name-or-unknown>
VERDICT: ERROR
REASON: Trail configuration is incomplete or unparseable — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws cloudtrail describe-trails --trail-name-list <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, first-fail wins)

### Step 0: Expert knowledge — non-obvious CloudTrail behaviors

These behaviors change classification if ignored:

- **`IsOrganizationTrail` is the org-coverage flag, not the multi-region flag.**
  Many operators conflate them. An org trail with `IsMultiRegionTrail: false`
  logs all accounts but only in the trail's home region — a lateral-movement
  attack in `ap-southeast-1` leaves zero trace. Both must be `true` for
  full org + full region coverage.

- **Org trail requires `organizations:EnableAWSServiceAccess` for CloudTrail.**
  If the AWS Organizations trusted-service access for CloudTrail was revoked
  (or never enabled), the trail appears active (`IsLogging: true`) but silently
  logs only the management account. Member-account events stop flowing. This is
  invisible in `describe-trails` — check `aws organizations list-aws-service-
  access-for-organization` for `SERVICE_PRINCIPAL: cloudtrail.amazonaws.com`.

- **S3 bucket policy must grant `s3:x-amz-acl: bucket-owner-full-control`.**
  Without this condition, log objects delivered on behalf of member accounts
  are owned by the member account, not the management account. The management
  account can list the objects (it owns the bucket) but cannot read them. This
  produces a trail that "looks fine" but whose logs are inaccessible for
  org-wide queries. The bucket policy must also allow `cloudtrail.amazonaws.com`
  to `s3:GetBucketAcl`, `s3:ListBucket`, and `s3:PutObject`.

- **`KmsKeyId` on the trail controls SSE-KMS for S3 log delivery, not
  CloudTrail event encryption.** This KMS key encrypts the log files at rest
  in S3. If `KmsKeyId` is null, S3 defaults to SSE-S3 (AES-256, Amazon-managed
  key). SSE-S3 is encryption, but it is not customer-controlled — a compliance
  framework requiring customer-managed keys (CMK) treats null KmsKeyId as
  NO_ENCRYPTION. The key must be in the same region as the trail and its policy
  must grant `cloudtrail.amazonaws.com` the `kms:GenerateDataKey*` and
  `kms:Decrypt` permissions with the CloudTrail trail ARN as condition.

- **Log file validation digest files live in a separate S3 prefix.** Digests
  are delivered to `<prefix>/CloudTrail-Digest/`. If an S3 lifecycle rule
  expires objects in the bucket prefix but does NOT exclude the digest
  sub-prefix, the digest chain breaks and `validate-logs` fails. A trail with
  `LogFileValidationEnabled: true` and expired digests provides a false sense
  of integrity.

- **CloudTrail Insights has its own billing dimension.** Insights is charged
  per management event analyzed, on top of the first-free-copy. This is why
  some orgs disable it despite the security value. The auditor flags its
  absence as NO_INSIGHTS regardless of cost rationale — the remediation can
  note the cost trade-off.

- **Insights selectors are a separate API call.** `describe-trails` does NOT
  return Insight selectors. You must call `get-insight-selectors --trail-name
  <name>` separately. If the input does not include insight-selector data, the
  auditor should note the gap but cannot definitively classify NO_INSIGHTS —
  request the data.

- **`IncludeGlobalServiceEvents: false` silently drops IAM, STS, Route 53, and
  CloudFront events.** These are "global" services whose events are logged in
  the trail's home region (us-east-1 for org trails). Disabling them removes
  the entire IAM/STS audit trail — the most security-critical event source.
  This is a CONFIG_GAP finding.

- **CloudWatch Logs retention is a log-group property, not a trail property.**
  The trail delivers to the log group, but retention is configured on the log
  group itself via `aws logs put-retention-policy`. A trail pointing to a log
  group with `retentionInDays: null` ("Never expire") has no compliance
  boundary on log lifetime — it accumulates indefinitely (cost + no
  data-retention governance). Flag as CONFIG_GAP.

- **The 5-trail-per-region quota.** An account can have at most 5 trails per
  region. If an org already has 5 trails in the management account's home
  region, creating a new org trail requires deleting one first. This is an
  operational constraint, not a security finding, but it may explain why an org
  trail is missing.

- **Trail ARN contains the management account ID, not the member account.**
  An org trail ARN is `arn:aws:cloudtrail:<region>:<mgmt-account>:trail/<name>`.
  When auditing from a member account, the trail will NOT appear in
  `describe-trails` — this does not mean it does not exist. Verify from the
  management account.

- **CloudTrail data events are NOT enabled by default — only management
  events are logged.** A "fully configured" org trail with every dimension
  green still records zero S3 `GetObject`/`PutObject`, Lambda `Invoke`, or
  DynamoDB `GetItem`/`PutItem` activity unless an event selector explicitly
  adds the data-resource ARNs (`s3:::*`, `lambda:::*`, `dynamodb:::*`). Data
  events also have a separate billing dimension. The auditor cannot classify
  data-event coverage from `describe-trails` — `get-event-selectors` is
  required. Absence of data-event selectors is not in the verdict matrix
  (it is a coverage gap, not a compliance gap), but it must be noted in
  FINDINGS as a blind-spot warning.

- **`lookup-events` API returns only the last 90 days and only management
  events.** Auditors who use `aws cloudtrail lookup-events` to verify
  "did this trail capture X?" get a misleadingly empty result for any event
  older than 90 days or for any data event regardless of age. The S3 log
  files are the authoritative long-term record — the lookup API is a
  short-term operational tool, not an audit-of-record.

- **Event selectors can silently exclude AWS KMS events.** KMS generates
  very high event volume (Decrypt/Encrypt per S3 GET/PUT under SSE-KMS), so
  legitimate `FieldByField` exclusions of `eventSource: kms.amazonaws.com`
  are common in event selectors. This is operationally reasonable but
  creates a forensics blind spot for KMS key abuse (e.g., decrypting
  exfiltrated ciphertext). The auditor should call `get-event-selectors`
  and surface any `ExcludeManagementEventSources` entry in FINDINGS as a
  WARNING — it is not a verdict failure, but the operator must acknowledge
  the trade-off.

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

**Verify the S3 bucket policy grants CloudTrail the required ACL condition
(this is invisible from `describe-trails` and silently breaks member-account
log access on org trails):**

```bash
aws s3api get-bucket-policy --bucket <S3BucketName> --query Policy --output text | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'
# Expected: an Allow on s3:PutObject with Condition StringEquals
#           s3:x-amz-acl == bucket-owner-full-control
aws kms describe-key --key-id <KmsKeyId> --query 'KeyMetadata.Policy' --output text | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'
# Expected: Allow on kms:GenerateDataKey*/kms:Decrypt with
#           EncryptionContext:aws:cloudtrail:arn == <trail-arn>
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

If Steps 1-3 passed, check Insights selectors:

- **No `InsightsSelectors` data provided** → The auditor cannot definitively
  classify the Insights dimension. **Fallback verdict: OK with a WARNING** in
  FINDINGS: "Insights selectors not provided — call
  `aws cloudtrail get-insight-selectors --trail-name <name>` and re-audit to
  close this dimension." Do NOT emit NO_INSIGHTS unless the input explicitly
  states selectors are absent/empty — guessing inflates false positives. The
  operator-facing REASON must say "Insights unverified (data missing)" so the
  fallback is auditable, not silent.

- **`InsightsSelectors` is empty (`[]`) or not configured** → No anomaly
  detection on API call volume or error rates. **Verdict: NO_INSIGHTS**
  (MEDIUM risk).

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
  They are separate API calls — checking only the config is a false OK.

- NEVER assume CloudTrail Insights works immediately after enablement. It
  requires a minimum 7-day baseline of management events before it can detect
  anomalies. A newly enabled Insights selector will not produce findings in
  the first week — this is normal, not a misconfiguration.

- NEVER conflate CloudTrail log retention with CloudWatch Logs retention.
  CloudTrail itself has no retention setting — logs persist in S3 until a
  lifecycle policy removes them. CloudWatch Logs retention is a separate
  property on the log group (`retentionInDays`). An audit that checks only
  the trail config for retention misses both dimensions.

- NEVER overlook the S3 bucket policy for org trails. The bucket must grant
  `cloudtrail.amazonaws.com` `s3:PutObject` with condition
  `s3:x-amz-acl: bucket-owner-full-control`. Without the ACL condition,
  member-account logs are owned by the member account and the management
  account cannot read them — the trail appears healthy but produces
  inaccessible logs.

- NEVER assume `IncludeGlobalServiceEvents: true` is the default in all
  tooling. Terraform and CloudFormation templates that create trails sometimes
  omit this field, and the default behavior varies by SDK version. Explicitly
  verify it is `true` — disabling it drops the entire IAM/STS audit trail.

- NEVER recommend deleting an existing org trail to "fix" a misconfiguration.
  Update the trail in place with `aws cloudtrail update-trail`. Deleting and
  recreating loses the trail name, S3 prefix continuity, and any CloudWatch
  alarms or EventBridge rules keyed to the trail ARN.

- NEVER ignore the KMS key policy when auditing CloudTrail KMS encryption.
  The key must grant `cloudtrail.amazonaws.com` the `kms:GenerateDataKey*`
  permission with the trail ARN in the condition. A `KmsKeyId` set on the
  trail with a missing or restrictive key policy causes silent log-delivery
  failure — the trail is "encrypted" but nothing is being written.

- NEVER classify NO_INSIGHTS if the insight-selector data was not provided.
  `describe-trails` does not return Insights selectors. If the input lacks
  `get-insight-selectors` output, note the gap and request the data rather
  than guessing.

- NEVER assume a single-region trail is sufficient for an org, even if all
  workloads are in one region. AWS global services (IAM, STS, Route 53) and
  cross-region API calls (e.g., a Lambda in us-east-1 assuming a role in
  eu-west-1) generate events in the source region. A single-region trail
  misses the cross-region activity entirely.

- NEVER overlook S3 lifecycle rules that expire the **log files themselves**,
  not just the digest prefix. A common compliance failure is a blanket
  `ExpirationInDays` rule on the whole bucket (or on `CloudTrail/` prefix)
  that deletes raw log files after 30/60/90 days while leaving digests
  intact — `validate-logs` then passes on a digest chain that points at
  missing log files, and the audit trail silently shortens. The auditor
  cannot see lifecycle rules from `describe-trails`; if S3 inventory or a
  lifecycle policy summary is available, surface any non-versioned expiry on
  the log prefix as a CONFIG_GAP finding.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-trail`, `start-logging`, `stop-logging`, `add-tags`, `put-insight-
  selectors`), the auditor MUST emit:
  `CONFIRM: About to <action> on trail <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`

- **Capture current trail config for rollback:**
  `aws cloudtrail describe-trails --trail-name-list <name> --output json >
  /tmp/<name>-backup-$(date +%s).json` BEFORE any modification. Trail updates
  are not versioned — there is no undo without a backup.

- **Enabling Insights incurs cost.** `put-insight-selectors` starts billing
  per management event analyzed. Surface this BEFORE the operator approves —
  do not silently enable a metered feature.

- **update-trail is atomic but irreversible.** Changing `KmsKeyId` from null
  to a key ARN re-enables SSE-KMS encryption going forward but does NOT
  re-encrypt existing log files already in S3. Old files remain under
  whatever encryption they were delivered with.

- **Org-trail enablement check.** Before recommending `update-trail
  --is-organization-trail`, verify the caller is in the management account
  and that `aws organizations describe-organization` returns a valid org.
  A member account cannot create or update an org trail.

- Prefer `update-trail` (in-place modification) over delete-and-recreate.
  In-place updates preserve the trail ARN, S3 prefix, and all downstream
  integrations (EventBridge, CloudWatch alarms, SIEM pipelines).

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

## Deep reference: CloudTrail internals

### Org trail creation and member-account visibility

When an org trail is created in the management account, CloudTrail
automatically creates a "shadow" trail in each member account with the same
name. These shadow trails are read-only — member-account users can see the
trail exists but cannot modify it. All logs flow to the management account's
S3 bucket. If Organizations trusted-service access is revoked, the shadow
trails remain visible but stop delivering member-account events.

### Log file validation mechanics

Each hour, CloudTrail delivers log files for the preceding hour's events.
When `LogFileValidationEnabled` is true, it also delivers a digest file
containing SHA-256 hashes of all log files delivered in that hour, plus the
hash of the previous hour's digest (hash chain). `validate-logs` walks the
chain from the start time to the end time, recomputes hashes, and reports
any mismatch. A broken chain (missing or modified digest) invalidates all
subsequent entries.

### Insights detection model

CloudTrail Insights analyzes management-event volumes using statistical
anomaly detection. It establishes a baseline of normal API call rates and
error rates per event source over a rolling window, then flags sustained
deviations (typically 3x+ over baseline for several minutes). It does NOT
analyze individual events for suspiciousness — that is the job of GuardDuty
or Security Hub. Insights detects "unusual volume," not "malicious activity."

### KMS encryption context for CloudTrail

CloudTrail uses the encryption context pair
`aws:cloudtrail:arn = <trail-arn>` when calling `kms:GenerateDataKey`. This
context is visible in CloudTrail's own KMS event logs and in the KMS key
policy condition. The key policy MUST allow CloudTrail service principal
with this exact context — a policy allowing `kms:GenerateDataKey*` without
the context condition is broader than necessary but functional.

## Domain

AWS CloudOps / CloudTrail Governance, Compliance & Forensic Readiness.
