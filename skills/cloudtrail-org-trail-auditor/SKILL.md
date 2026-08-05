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
    Pre-compliance review of an AWS Organizations CloudTrail trail's
    configuration: org-wide coverage, multi-region logging, KMS-encryption,
    log-file integrity validation, Insights enablement, and log retention
    posture.
  when_not_to_use:
    - "Single-account trail that is NOT part of an AWS Organization (different audit scope)."
    - "CloudTrail Lake event-data-store queries (different API surface: list-event-data-stores / start-query)."
    - "Configuring data-event selectors for S3/Lambda/DynamoDB resources (separate skill)."
    - "Macie, GuardDuty, or Security Hub finding triage (use the dedicated triage skills)."
    - "Cost-optimization of CloudTrail ingest volume (use a cost-audit skill)."
  activation_triggers:
    - "audit this CloudTrail org trail"
    - "is my org trail configured correctly"
    - "check CloudTrail org trail log file validation"
    - "is the CloudTrail org trail encrypted with KMS"
    - "are CloudTrail Insights enabled on the org trail"
    - "CloudTrail multi-region check on the org trail"
    - "CloudTrail org trail coverage audit"
    - "verify CloudTrail forensic readiness for the org"
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
  An org trail with `IsMultiRegionTrail: false` logs all accounts but only in
  the trail's home region — a lateral-movement attack in `ap-southeast-1`
  leaves zero trace. Both must be `true` for full org + full region coverage.

- **Org trail requires `organizations:EnableAWSServiceAccess` for CloudTrail.**
  If Organizations trusted-service access for CloudTrail is revoked, the trail
  appears active (`IsLogging: true`) but silently logs only the management
  account. Invisible in `describe-trails` — check `aws organizations
  list-aws-service-access-for-organization` for
  `SERVICE_PRINCIPAL: cloudtrail.amazonaws.com`.

- **S3 bucket policy must grant `s3:x-amz-acl: bucket-owner-full-control`.**
  Without this condition, log objects delivered on behalf of member accounts
  are owned by the member account, not the management account. The management
  account can list the objects (it owns the bucket) but cannot read them. The
  bucket policy must also allow `cloudtrail.amazonaws.com` to `s3:GetBucketAcl`,
  `s3:ListBucket`, and `s3:PutObject`.

- **`KmsKeyId` controls SSE-KMS for S3 log delivery, not "CloudTrail event
  encryption."** If `KmsKeyId` is null, S3 defaults to SSE-S3 (AES-256,
  Amazon-managed key). SSE-S3 IS encryption, but it is not customer-controlled
  — a compliance framework requiring customer-managed keys treats null
  `KmsKeyId` as NO_ENCRYPTION. The key must be in the trail's region and its
  policy must grant `cloudtrail.amazonaws.com` the `kms:GenerateDataKey*` and
  `kms:Decrypt` permissions with the CloudTrail trail ARN as encryption
  context (`kms:EncryptionContext:aws:cloudtrail:arn = <trail-arn>`).

- **Log file validation digest files live in a separate S3 prefix.** Digests
  are delivered to `<prefix>/CloudTrail-Digest/`. If an S3 lifecycle rule
  expires objects in the bucket prefix but does NOT exclude the digest
  sub-prefix, the digest chain breaks and `validate-logs` fails. A trail with
  `LogFileValidationEnabled: true` and expired digests provides a false sense
  of integrity.

- **CloudTrail Insights has its own billing dimension** (per management event
  analyzed, on top of the first-free-copy). Some orgs disable it for cost;
  the auditor still flags absence as NO_INSIGHTS — remediation can note the
  cost trade-off.

- **Insights selectors are a separate API call.** `describe-trails` does NOT
  return them — call `get-insight-selectors --trail-name <name>` separately.

- **`IncludeGlobalServiceEvents: false` silently drops IAM, STS, Route 53, and
  CloudFront events.** These global-service events are logged in the trail's
  home region (us-east-1 for org trails). Disabling them removes the entire
  IAM/STS audit trail. This is a CONFIG_GAP finding.

- **CloudWatch Logs retention is a log-group property, not a trail property.**
  A trail pointing to a log group with `retentionInDays: null` ("Never
  expire") has no compliance boundary on log lifetime. Flag as CONFIG_GAP.

- **The 5-trail-per-region quota** is a hard limit. An account with 5 trails
  in a region cannot create another without deleting one. Operational
  constraint — not a security finding, but may explain a missing org trail.

- **Trail ARN contains the management account ID, not the member account.**
  When auditing from a member account, the org trail will NOT appear in
  `describe-trails` — verify from the management account.

- **CloudTrail data events are NOT enabled by default — only management
  events are logged.** A "fully configured" org trail still records zero S3
  `GetObject`/`PutObject`, Lambda `Invoke`, or DynamoDB activity unless an
  event selector adds the data-resource ARNs. `get-event-selectors` is
  required; absence is a coverage gap (note in FINDINGS), not a verdict
  failure.

- **`lookup-events` API returns only the last 90 days and only management
  events.** Auditors using it to verify "did this trail capture X?" get a
  misleadingly empty result for any event older than 90 days or any data
  event. The S3 log files are the authoritative long-term record.

- **Event selectors can silently exclude AWS KMS events.** KMS generates very
  high event volume (Decrypt/Encrypt per S3 GET/PUT under SSE-KMS), so
  legitimate `ExcludeManagementEventSources: kms.amazonaws.com` entries are
  common. This is operationally reasonable but creates a forensics blind spot
  for KMS key abuse. Surface any exclusion in FINDINGS as a WARNING.

- **`describe-trails` (LIST) and `get-trail` (GET) return different fields.**
  `describe-trails` returns a summary list; `get-trail --name <name>` returns
  the full `Trail` object including the full KMS context. For an authoritative
  per-trail audit, prefer `get-trail` — `describe-trails` has been observed to
  omit fields on trails created by CloudFormation stacks that set advanced
  event selectors.

- **First management-event copy is free per region, per account; a second
  management-events trail in the same region incurs per-event billing.** A
  common cost trap: an operator creates a "backup" org trail pointing to a
  different bucket — silent double billing starts immediately. Surface a
  WARNING if the input reveals multiple trails in one region.

- **CloudTrail event delivery latency is typically 3–15 minutes, NOT the
  "hourly" many operators assume.** The hourly window is the file-batching
  cadence, but events for that window can land up to 15 minutes after the API
  call. Operators investigating "did X happen in the last 5 minutes?" cannot
  rely on CloudTrail — use CloudWatch Metrics or EventBridge for near-real-time
  detection. This is also why `IsLogging: true` does not guarantee that
  recently tested events are already in S3.

- **`validate-logs` requires `s3:GetObject` on BOTH the log-file prefix AND
  the digest prefix.** Most scoped-down audit roles grant only the log prefix
  and silently fail validation with a generic "AccessDenied" buried in the
  output. Verify the calling identity's role covers
  `s3://<bucket>/<prefix>/CloudTrail-Digest/*` as well as the log prefix.

- **Org-trail enablement propagation delay.** Flipping
  `--is-organization-trail` on an existing trail takes 5–15 minutes before
  shadow trails appear in member accounts and event delivery from member
  accounts begins. An audit run in that window reports NO member-account
  events even though configuration is correct — note this when classifying
  a recently converted trail.

- **CloudTrail log files use S3 multipart upload.** Subscribers wiring
  EventBridge or S3 event notifications on the log prefix may receive
  `s3:ObjectCreated:*` for the initiate-multipart-upload, not the
  complete-multipart-upload — subscribers see partial or empty objects. SIEM
  integrations should trigger on `CompleteMultipartUpload` only.

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

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-trail`, `start-logging`, `stop-logging`, `add-tags`, `put-insight-
  selectors`), the auditor MUST emit:
  `CONFIRM: About to <action> on trail <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)` and wait for an explicit `yes`
  before emitting the CLI. Treat `delete-trail` as BLOCKED — see the NEVER
  list.

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

## Recent AWS features (2024-2026)

- **CloudTrail Lake (2024-2025):** CloudTrail Lake enables SQL-based querying of event data without S3/Athena. Auditors should verify that CloudTrail Lake is configured as a supplementary query surface, and that its retention period meets compliance requirements — Lake has its own separate retention independent of the S3 trail.
- **Expanded data event coverage (2024-2025):** CloudTrail now records data events for additional resource types including S3 directory buckets, Lambda layers, and CloudFront KeyValueStore. Auditors should verify that data event logging covers these new resource types where applicable.
- **CloudTrail Insights enhancements (2024):** Insights now supports anomaly detection on write management events with improved accuracy. Auditors should re-evaluate whether Insights is enabled on all organization trails — it is often overlooked.
- **Federation with CloudTrail Lake:** Lake now supports cross-account and cross-org event federation. Auditors should verify that the federation configuration includes all member accounts and that no accounts are silently excluded.

## Domain

AWS CloudOps / CloudTrail Governance, Compliance & Forensic Readiness.
