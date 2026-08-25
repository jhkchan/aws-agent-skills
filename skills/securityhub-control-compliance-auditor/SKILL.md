---
name: securityhub-control-compliance-auditor
description: Audits AWS Security Hub control compliance findings and maps each to a deterministic compliance verdict (FAILED | WARNING | PASSED | NOT_APPLICABLE), then maps every FAILED / WARNING control to a specific fix action. Handles the full Security Hub finding lifecycle — active findings, suppressed findings, resolved-but-still-failing, archived findings, NOT_AVAILABLE with StatusReasons, multi-account aggregation, and cross-standard control families (FSBP, CIS, PCI-DSS, NIST 800-53). Use when reviewing Security Hub control status, triaging a compliance gap report, mapping findings to remediation runbooks, or preparing for an audit / executive compliance summary.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline classification — the skill reasons over provided Security Hub finding JSON (ASFF). For live-account audits, AWS CLI v2 with securityhub access (ListEnabledStandards, GetEnabledStandards, GetFindings, batch-update-findings) and SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: FAILED | WARNING | PASSED | NOT_APPLICABLE
  when_to_use: Reviewing Security Hub control compliance status, triaging a compliance gap report, mapping findings to remediation actions, auditing finding lifecycle states (suppressed / resolved / archived), preparing for a compliance audit, or generating an executive compliance summary across FSBP / CIS / PCI-DSS / NIST standards.
  version: 0.2.0
  author: Jacky Chan — AWS Community Builder
  keywords: Security Hub, compliance, control status, FSBP, Foundational Security Best Practices, CIS Benchmark, PCI-DSS, NIST 800-53, ASFF, finding lifecycle, suppression, remediation runbook, compliance verdict, NOT_AVAILABLE, StatusReasons, Workflow Status, Record State, delegated administrator
  tags: aws, securityhub, security, compliance, fsbp, cis, pci-dss, nist, audit, remediation, asff
---

# Security Hub Control-Compliance Auditor

> **Structural pattern:** ASFF Audit Pipeline — Activation → Output Contract →
> Mindset → Decision Tree → Process Steps → Reference Tables → Anti-Patterns →
> Safety Checks. Read top-to-bottom for a cold start; jump to the Decision Tree
> for a single finding.

## Quick Start (the 3 rules that prevent 80% of misclassifications)

1. **NOT_AVAILABLE is NOT the same as NOT_APPLICABLE.** Check
   `StatusReasons[].Code`: `NO_RESOURCES`/`DISABLED_CONTROL` →
   NOT_APPLICABLE; everything else (especially
   `SUPPORTED_SERVICE_NOT_ENABLED`) → WARNING.
2. **SUPPRESSED + FAILED is WARNING, never PASSED.** Suppression hides the
   finding but the control is still failing.
3. **ARCHIVED is always NOT_APPLICABLE.** The resource was deleted or the
   control superseded — historical state, not current posture.

Full classification: see Decision Tree below. Detailed reasoning: see
Process steps. Fix actions: see Control-to-fix-action mapping.

## Activation

Invoke when the input contains a Security Hub finding in ASFF format —
detected by ANY of these signals:

1. JSON with `Compliance.Status`, `Workflow.Status`, or `RecordState` keys.
2. `GeneratorId` matching the ARN regex
   `arn:aws:securityhub:::ruleset/(foundational-security-best-practices|cis-aws-foundations|pci-dss|nist)/(v/[\d.]+/)?[A-Z]+\d+\.\d+`
   (case-insensitive).
3. `ProductArn` containing `product/aws/securityhub`.
4. Explicit user mention of "Security Hub", "FSBP", "CIS Benchmark",
   "control compliance", or "compliance gap report".

Do NOT invoke for: raw CloudTrail events, generic IAM policy JSON without a
Security Hub wrapper, AWS Audit Manager findings, or Config rule
compliance JSON (those lack the ASFF `Compliance` block — use Config-specific
skills instead).

## Output Contract (CRITICAL — read before any classification)

Every finding MUST produce this EXACT output block. An agent that omits
any field fails the audit. Copy this template verbatim and fill the
placeholders:

```text
CONTROL: <ControlId from GeneratorId, e.g. S3.2>
VERDICT: <FAILED | WARNING | PASSED | NOT_APPLICABLE>
REASON: <Rule number + the specific field values that drove the verdict.
MUST cite Compliance.Status, Workflow.Status, RecordState, and StatusReasons
code if applicable. For SUPPRESSED findings, MUST include whether a Workflow
Note is present and its content or absence. 1-2 sentences.>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>
REMEDIATION: <Specific fix action from the control-to-fix-action table, or
"None required — control is compliant" for PASSED, or
"None required — control does not apply" for NOT_APPLICABLE.>
```

Rules for filling the template:
- ALWAYS include ALL FIVE headers (`CONTROL`, `VERDICT`, `REASON`, `SEVERITY`,
  `REMEDIATION`) even when the finding is PASSED or NOT_APPLICABLE — a blank
  `REMEDIATION: None required` is correct, but omitting the header is a
  contract violation.
- The `VERDICT` value must be ONE of exactly four tokens: `FAILED`,
  `WARNING`, `PASSED`, `NOT_APPLICABLE`. Never output compound statuses like
  `WARNING (PENDING)` or `NOT_APPLICABLE/ARCHIVED`.
- For SUPPRESSED findings, the REASON field MUST mention the suppression
  context: whether `Workflow.Note` is present, its author/date, or explicitly
  state "Suppression has no documented justification." Omitting the
  suppression context from a SUPPRESSED finding is a contract violation.
- Never prefix the block with conversational text ("Sure, here is the
  audit...") or disclaimers ("I cannot access..."). Start directly with
  `CONTROL:`.

## Mindset

Classify each AWS Security Hub control finding against a four-state compliance
verdict, then map every actionable verdict to a concrete fix action. The core
insight that separates this skill from naive pass-through of
`Compliance.Status` is that **Security Hub stores multiple overlapping states
on every finding** — `Compliance.Status`, `Workflow.Status`, `RecordState`,
and `Compliance.StatusReasons` — and each combination tells a different
operational story. A `FAILED` finding that is `ARCHIVED` is not a current
failure. A `FAILED` finding that is `SUPPRESSED` is not a pass. A `RESOLVED`
finding that is still `FAILED` is a WARNING, not a success.

The auditor must read all four fields in the correct order — the same order
that a Security Hub engineer triages the findings dashboard — and produce a
verdict that reflects the **current, real-world compliance posture**, not just
the raw status string.

## Decision Tree (classification flow)

Apply top-to-bottom. First matching rule wins.

```
START
  │
  ├─ Compliance block missing? ───────────────► NOT_APPLICABLE (integration finding)
  │
  ├─ RecordState = ARCHIVED? ─────────────────► NOT_APPLICABLE (stale)
  │
  ├─ Workflow.Status = SUPPRESSED + FAILED? ──► WARNING (governance flag)
  │
  ├─ Workflow.Status = RESOLVED + FAILED? ────► WARNING (>48h → FAILED)
  │
  ├─ Compliance.Status = NOT_AVAILABLE?
  │    ├─ NO_RESOURCES / DISABLED_CONTROL ────► NOT_APPLICABLE
  │    ├─ UNSUPPORTED_INSTANCE_TYPE ─────────► NOT_APPLICABLE
  │    ├─ SUPPORTED_SERVICE_NOT_ENABLED ──────► WARNING (Config gap)
  │    ├─ ASSUME_ROLE_ERROR / PERMISSION_DENIED► WARNING
  │    ├─ CONFIG_RETURNS_UNKNOWN ─────────────► WARNING
  │    ├─ ASSESSMENT_FAILED ──────────────────► WARNING
  │    ├─ SECURITY_HUB_NOT_ENABLED_IN_REGION ─► WARNING
  │    └─ empty / absent ─────────────────────► WARNING (ambiguous)
  │
  ├─ Compliance.Status = FAILED? ─────────────► FAILED
  ├─ Compliance.Status = WARNING? ────────────► WARNING
  ├─ Compliance.Status = PASSED? ─────────────► PASSED
  │
  └─ (unrecognized status) ───────────────────► WARNING + "unrecognized Compliance.Status"
```

**Two rules that cause the most misclassifications — always double-check:**
- `NOT_AVAILABLE` + `SUPPORTED_SERVICE_NOT_ENABLED` = **WARNING** (not
  NOT_APPLICABLE — Config being disabled is a monitoring gap).
- `SUPPRESSED` + `FAILED` = **WARNING** (not PASSED — suppression hides but
  does not fix).

## Process — Classification logic (reference for each step)

### Step 0 — Validate input, detect edge cases

Verify the input is an ASFF record. Edge cases to handle before
classification:

**Malformed JSON:** If the finding JSON cannot be parsed, output:
```text
CONTROL: <unknown>
VERDICT: WARNING
REASON: Input JSON is malformed — cannot extract Compliance block. Triage manually.
SEVERITY: MEDIUM
REMEDIATION: Re-fetch the finding via GetFindings by finding ID. If the source
integration is sending malformed ASFF, open a support case.
```

**Missing Compliance block:** If the `Compliance` key is absent entirely,
the finding is an **integration finding** (GuardDuty, Inspector, Macie,
Detective, Firewall Manager) or a custom product finding. It is a security
event, not a control compliance evaluation:
```text
CONTROL: <ProductFields.ControlId or GeneratorId>
VERDICT: NOT_APPLICABLE
REASON: Finding has no Compliance block — this is an integration or custom
product finding, not a Security Hub control evaluation.
SEVERITY: <from Severity.Label, or INFORMATIONAL if missing>
REMEDIATION: Route to the appropriate detector skill (GuardDuty, Inspector).
```

**Schema version check:** Verify `SchemaVersion = 2018-10-08` (the only ASFF
version). If older or missing, flag it — `Compliance.StatusReasons` was added
to the schema in late 2020, so findings created before that may lack
StatusReasons even on NOT_AVAILABLE. Append a note: "Pre-2020 schema —
StatusReasons may be absent."

**Malformed ARN fields:** If the finding `Id` or `Resources[].Id` does not
match the AWS ARN pattern
`arn:aws:[a-z0-9-]+:[a-z]{2}-[a-z]+-\d:\d{12}:.*`, append:
```
DATA_QUALITY: Finding Id / Resource Id does not match expected ARN format.
Verify the source integration is producing valid ASFF.
```
This does not change the verdict — it is a data-quality flag.

**Unexpected enum values:** If `Compliance.Status` is not one of
`PASSED | WARNING | FAILED | NOT_AVAILABLE`, emit WARNING with:
"Unrecognized Compliance.Status `<value>` — not a valid ASFF enum. Triage
manually." Do NOT guess the intent.

**Field-defaulting rules (apply when a field is absent but non-fatal):**
- `Compliance.StatusReasons` missing on NOT_AVAILABLE → WARNING with
  "NOT_AVAILABLE with no StatusReasons — cannot determine whether the control
  is inapplicable or failed to evaluate." Do NOT default to NOT_APPLICABLE —
  the absence of a reason code is ambiguous, not a signal of non-applicability.
  This is the most common false-positive source: treating "I don't know why"
  as "it doesn't apply."
- `RecordState` missing → treat as ACTIVE (Security Hub default).
- `Workflow.Status` missing → treat as NEW (default).
- `UpdatedAt` missing → cannot compute staleness. Emit the verdict from other
  fields but append STALE_FLAG: "UpdatedAt absent — cannot verify freshness."
- `Severity.Label` missing → default to MEDIUM (conservative midpoint), note:
  "MEDIUM (assumed — label absent)".

### Step 1 — RecordState = ARCHIVED → NOT_APPLICABLE (stale)

Security Hub archives findings when the resource was deleted, the control was
disabled, or the finding was superseded by a newer one. An archived finding
represents a **historical** state. If `RecordState = ARCHIVED`, emit
**NOT_APPLICABLE** regardless of `Compliance.Status`.

Cite "Rule 1: archived — resource deleted or control superseded".

**Freshness guard:** even if `RecordState = ACTIVE`, check `UpdatedAt`. If the
finding has not been updated in > 30 days, the Security Hub service may have
stopped refreshing (account removed from delegated admin, control disabled
and re-enabled). Append:
```
STALE_FLAG: Finding last updated <date> (>30 days ago). Verify the control is
still enabled and Security Hub is refreshing in this region.
```

**Deprecated-standard edge case (expert):** When a standard version is
deprecated (e.g., CIS v1.2.0 → v2.0.0 migration in Q4 2024), existing
findings for the old standard's controls show as ARCHIVED but may persist in
the datastore for 90 days. These are NOT current failures — classify as
NOT_APPLICABLE with note "control belongs to deprecated standard version."

### Step 2 — Suppressed failure → WARNING (governance flag)

If `Workflow.Status = SUPPRESSED` AND `Compliance.Status = FAILED`, emit
**WARNING**. This is the single most misunderstood Security Hub state.
Suppression hides the finding from the default dashboard view, but **the
control is still failing**. Suppression is an operational triage decision
(accepted risk, compensating control, false positive), not a remediation.

Cite "Rule 2: suppressed FAILED — governance concern". Always include in the
REASON whether the suppression has a `Note`:

- If `Workflow.Note` is present, cite it (e.g., "Suppressed by
  securityops@example.com on 2026-06-15: 'Accepted risk — compensating
  control via WAF rule arn:aws:wafv2:...'").
- If no `Note`, flag: "Suppression has no documented justification — review
  whether the suppression is still valid."
- Security Hub does not natively expire suppressions. A suppression created
  months ago for a temporary exception may still be hiding a failing control.

**Suppression lifecycle heuristic (expert):** Security Hub has **no
suppression TTL** — unlike GuardDuty which auto-archives, suppressions persist
indefinitely until manually cleared. In large organizations, 40-60% of
suppressed findings are stale exceptions that no longer apply. The validity
heuristic:

- **< 30 days + has Note + resource unchanged** → likely valid. Do not
  unsuppress.
- **30-90 days + has Note** → review. Check whether the compensating control
  (WAF rule, SCP, permissions boundary) still exists. If removed, the
  suppression is invalid.
- **> 90 days + has Note** → stale. Recommend re-evaluation: unsuppress, let
  Security Hub re-run the check, re-suppress only if still justified.
- **Any age + no Note** → immediately suspect. An undocumented suppression is
  indistinguishable from hiding a finding. Unsuppress and re-evaluate.

### Step 3 — Resolved but still FAILED → WARNING (pending re-evaluation)

If `Workflow.Status = RESOLVED` AND `Compliance.Status = FAILED`, emit
**WARNING**. The operator marked the finding resolved (remediation applied),
but Security Hub has not yet re-evaluated the control.

Security Hub re-runs control checks every **12 to 24 hours** (the Config rule
evaluation trigger determines the exact interval — see Config-rule evaluation
triggers reference). If the finding was marked `RESOLVED` more than 48 hours
ago and is still `FAILED`, the remediation likely **failed** — escalate to
**FAILED** and note: "Resolution marked >48h ago but control still FAILED —
remediation likely incomplete. Re-investigate the resource directly."

**Config-change vs periodic controls (expert distinction):** The 48h
threshold is conservative. Config-change-triggered controls re-evaluate within
5-30 minutes of a resource change. If a config-change control is still FAILED
1 hour after RESOLVED was marked, the fix already failed — do not wait 48h.
For periodic controls (CloudTrail, Config, IAM password policy), the full 24h
window is needed. The 48h global threshold covers the worst case.

### Step 4 — NOT_AVAILABLE → split by StatusReasons

`Compliance.Status = NOT_AVAILABLE` means Security Hub **could not produce a
definitive PASSED/FAILED**. The reason matters — it splits into two verdicts:

**NOT_APPLICABLE** (control genuinely does not apply):
- `NO_RESOURCES` — zero resources in scope. Example: Redshift.1 with no
  Redshift clusters.
- `DISABLED_CONTROL` — control disabled by the delegated administrator (or
  via Security Hub Central Configuration).
- `UNSUPPORTED_INSTANCE_TYPE` — resource exists but the control does not
  evaluate this variant.

**WARNING** (Security Hub tried and failed — needs investigation):
- `SUPPORTED_SERVICE_NOT_ENABLED` — AWS Config not enabled in the region. The
  control cannot run — a monitoring posture misconfiguration, not a pass.
- `CONFIG_RETURNS_UNKNOWN` — Config rule returned UNKNOWN (transient error or
  permissions issue with the Config service-linked role).
- `ASSESSMENT_FAILED` — assessment threw an error. Often transient but may
  indicate systemic problems (permissions, throttling).
- `ASSUME_ROLE_ERROR` or `PERMISSION_DENIED` — service-linked role lacks
  permissions to evaluate the resource.
- `SECURITY_HUB_NOT_ENABLED_IN_REGION` — Hub disabled in the region.
- `CANNOT_ENABLE_RECORDS` — cannot enable Config recording.
- `UNKNOWN_CONTROL_STATUS` — undetermined, investigate.
- StatusReasons empty or absent → WARNING: "NOT_AVAILABLE with no
  StatusReasons — investigate manually."

**Full StatusReason code reference:**

| Code | Verdict | Meaning |
|---|---|---|
| `NO_RESOURCES` | NOT_APPLICABLE | Zero resources in scope |
| `DISABLED_CONTROL` | NOT_APPLICABLE | Control disabled by admin / SHCC |
| `UNSUPPORTED_INSTANCE_TYPE` | NOT_APPLICABLE | Resource variant not evaluated |
| `SUPPORTED_SERVICE_NOT_ENABLED` | WARNING | AWS Config not enabled |
| `CONFIG_RETURNS_UNKNOWN` | WARNING | Config rule returned UNKNOWN |
| `ASSESSMENT_FAILED` | WARNING | Assessment threw an error |
| `ASSUME_ROLE_ERROR` | WARNING | Service-linked role cannot assume |
| `PERMISSION_DENIED` | WARNING | Insufficient IAM permissions |
| `SECURITY_HUB_NOT_ENABLED_IN_REGION` | WARNING | Hub disabled in region |
| `CANNOT_ENABLE_RECORDS` | WARNING | Cannot enable Config recording |
| `UNKNOWN_CONTROL_STATUS` | WARNING | Undetermined — investigate |

Cite "Rule 4: NOT_AVAILABLE — <code>".

### Step 5 — Compliance.Status = FAILED → FAILED

`RecordState = ACTIVE`, `Workflow.Status ∈ {NEW, NOTIFIED}`,
`Compliance.Status = FAILED`. The control is currently failing and has not
been triaged. Emit **FAILED**.

Cite "Rule 5: active FAILED — control is non-compliant". Map to the
fix-action table for the specific remediation.

### Step 6 — Compliance.Status = WARNING → WARNING

Security Hub uses `WARNING` for partially compliant controls or informational
concerns. Example: a CloudTrail trail exists but log validation is disabled.
Emit **WARNING**.

Cite "Rule 6: WARNING — partial compliance or informational concern".

### Step 7 — Compliance.Status = PASSED → PASSED

`Compliance.Status = PASSED` AND `RecordState = ACTIVE`. The resource is
fully compliant. Emit **PASSED** with `REMEDIATION: None required — control
is compliant`.

### Step 8 — Aggregation (multi-finding rollup)

When auditing multiple findings for the same control across resources, or
multiple controls across an account, the aggregate verdict is the **worst
verdict**:

```
FAILED > WARNING > PASSED > NOT_APPLICABLE
```

Report the count of each verdict in the aggregate:
```text
CONTROL: <ControlId>
AGGREGATE VERDICT: FAILED
BREAKDOWN: 3 FAILED, 1 WARNING, 12 PASSED, 2 NOT_APPLICABLE (across 18 resources)
```

## Severity escalation matrix

The `Severity.Label` determines remediation priority when combined with the
verdict:

| Verdict | Severity | Priority | SLA Guidance |
|---|---|---|---|
| FAILED | CRITICAL | P0 | Immediate (within 24h) — active exploit risk |
| FAILED | HIGH | P1 | Urgent (within 72h) — significant exposure |
| FAILED | MEDIUM | P2 | This sprint — compliance gap |
| FAILED | LOW | P3 | Next sprint — hardening |
| WARNING | CRITICAL/HIGH | P2 | This sprint — suppressed or pending |
| WARNING | MEDIUM/LOW | P3 | Next sprint — informational |
| PASSED | * | — | No action |

**Expert note on control severity vs finding severity:** The same control may
carry different severity labels across standards. EC2.15 (SSH 0.0.0.0/0) is
HIGH in FSBP but CRITICAL in PCI-DSS (`PCI.EC2.1`). When a resource is
flagged by multiple standards, use the **highest severity** across all
standards for prioritization.

**Blast-radius escalation rules:**

1. **Aggregate escalation:** A single `FAILED` control on N > 10 resources
   is a systemic configuration issue — escalate priority by one level (P3 →
   P2, P2 → P1) regardless of individual severity.
2. **Time-decay escalation:** A `FAILED` finding with `FirstObservedAt` older
   than 90 days has been ignored for a quarter — escalate by one level.
3. **Critical-inheritance escalation:** If a `FAILED` control is on a
   **trust-boundary resource** (IAM role with cross-account trust, KMS key
   with wildcard policy, S3 bucket with public write), escalate to P0
   regardless of the control's own severity.

## Config-rule evaluation triggers (expert reference)

Every Security Hub control is backed by an AWS Config managed rule. The
rule's evaluation trigger determines how quickly a fix is reflected:

**Configuration-change-triggered** (re-evaluate within minutes of a resource
change):
- S3.1-S3.8 (bucket settings — BPA, versioning, encryption, ACLs)
- EC2.2, EC2.15 (security groups)
- IAM.1-IAM.8 (IAM resources)
- KMS.1-KMS.2 (key policy / rotation)
- Lambda.1-Lambda.2 (function configuration)

**Periodic-triggered** (re-evaluate every 6-24 hours regardless of changes):
- CloudTrail.1-CloudTrail.9 (trail status)
- Config.1-Config.2 (recorder status)
- IAM.7 (password policy)
- CloudWatch.1-CloudWatch.14 (metric filters + alarms)
- EC2.4 (SSM managed-instance compliance)

**Operational implication:** When you mark a finding `RESOLVED` after a fix:
- Config-change controls: finding should flip to `PASSED` within **5-30
  minutes**. If still `FAILED` after 1 hour, the fix failed.
- Periodic controls: may take **up to 24 hours** to re-evaluate. Do not
  escalate until 24h for periodic (vs. 1h for config-change).

You can verify a control's evaluation mode via
`aws configservice describe-config-rules --config-rule-names <rule-name>`
and checking the `Source.Owner` + `MaximumExecutionFrequency`.

## Security Hub internals (non-obvious operational knowledge)

These behaviors are not in the public AWS documentation but cause real
production incidents. Internalize them before running a large-scale audit.

**Finding deduplication:** Security Hub deduplicates findings by a composite
key: `ProductArn` + `AwsAccountId` + `Region` + resource ARN + generator ID.
This means two findings for the **same resource** from the **same standard**
in the **same region** are always deduplicated — only the most recent
update survives. If you see a finding disappear after applying a fix, it was
not deleted; the re-evaluation replaced it. When auditing, deduplicate by
this composite key before counting to avoid double-counting the same
control-resource pair.

**BatchUpdateFindings race condition:** When you set `Workflow.Status =
RESOLVED` and the Config rule re-evaluates within the same second, the Config
evaluation can overwrite your workflow status back to `NEW`. This is a known
Security Hub behavior — Config-driven updates take precedence over manual
`BatchUpdateFindings` calls when they arrive within the evaluation window.
Mitigation: wait 60 seconds after the Config rule evaluation completes
(check `describe-config-rule-evaluation-status`) before marking RESOLVED.

**Config evaluation backlog:** After a large infrastructure change (Terraform
apply, CloudFormation stack update), Config rule evaluations queue up. The
backlog can delay finding updates by **2-6 hours** in accounts with >1000
resources. Check backlog via
`aws configservice describe-config-rule-evaluation-status` — if
`LastSuccessfulInvocationTime` is hours behind `LastErrorCode`, the rule is
backlogged. Do not interpret stale findings as failures during a backlog;
append a STALE_FLAG instead.

**Ingestion pipeline latency:** The path from Config rule evaluation to
Security Hub finding update has 3 stages with measurable latency:
1. Config rule evaluation: 1-30 min (config-change) or 6-24h (periodic).
2. Security Hub ingestion: ~30 seconds after Config publishes the result.
3. Finding aggregation (cross-region): ~5 minutes if `FindingAggregator`
   is configured.
Total worst-case: 24h + 30s + 5min ≈ 24h06m. This is why the Step 3
threshold is 48h — it provides a 2x safety margin over the theoretical
worst case.

**Automation rules silent suppression:** Security Hub automation rules
(formerly ingestion filters) can auto-suppress or auto-archive findings on
arrival, before they appear in `GetFindings`. A finding that arrives as
`SUPPRESSED` with no `Note` may have been suppressed by an automation rule,
not a human operator. Check
`aws securityhub list-automation-rules --region <region>` to audit active
rules. If an automation rule is suppressing a FAILED control, the
suppression is still a WARNING — automation does not change the verdict
logic, only the initial Workflow.Status.

**Control enablement cost model (budgeting insight):** Security Hub charges
$0.0010 per control check per region per month for FSBP. An account with all
~300 FSBP controls enabled across 16 regions generates ~$58/month in
Security Hub charges alone (300 × 16 × $0.0010 × 30 days). CIS, PCI, and
NIST each add their own per-check charges. For Organizations with 100+
member accounts, selective control enablement (enabled in active regions
only) reduces cost by 60-80% versus blanket enable-all.

## Finding correlation and root-cause grouping

When auditing multiple findings, group by **root cause** rather than control
ID. A single misconfiguration often triggers multiple controls:

**Example: S3 bucket without BPA**
- S3.1 (account BPA) → FAILED
- S3.2 (bucket BPA) → FAILED
- S3.6 (public ACL) → FAILED
- S3.8 (SSL policy) → FAILED

All four trace to one root cause: **BPA not enabled**. Enabling BPA fixes
all four on the next evaluation cycle.

**Root-cause grouping rules:**
1. Same `Resources[].Id` → single resource misconfiguration.
2. Same `AwsAccountId` + same control family (e.g., all S3.*) → check for
   account-level policy gap (account BPA, password policy).
3. `NOT_AVAILABLE` with `SUPPORTED_SERVICE_NOT_ENABLED` across multiple
   controls → root cause is Config being disabled. Fix Config once.
4. Cross-standard duplicates (FSBP + CIS + PCI flag same resource + issue)
   → one fix, independent re-evaluation per standard.

Correlation does NOT change individual verdicts — each finding still gets its
own verdict. Correlation only affects remediation batching.

## Coverage assessment heuristic

```
coverage_score = PASSED / (PASSED + FAILED + WARNING)
```

Exclude `NOT_APPLICABLE` from the denominator. Operational benchmarks:
- **>= 90%** → healthy. Focus on remaining FAILED / WARNING.
- **70-89%** → moderate gap. Apply root-cause grouping to find top 2-3
  drivers.
- **< 70%** → systemic failure. Prioritize enabling foundational controls
  (Config, CloudTrail, IAM password policy, S3 BPA) before chasing individual
  findings.

## Control-to-fix-action mapping

For every FAILED or WARNING control, map to the specific remediation action.

### FSBP (Foundational Security Best Practices)

| Control ID | Title | Fix Action | CLI Command |
|---|---|---|---|
| S3.1 | Account-level BPA | Enable all 4 BPA settings | `aws s3control put-public-access-block --account-id <id> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true` |
| S3.2 | Bucket-level BPA | Enable all 4 BPA settings on bucket | `aws s3api put-public-access-block --bucket <name> --public-access-block-configuration BlockPublicAcls=true,...` |
| S3.4 | Bucket versioning | Enable versioning | `aws s3api put-bucket-versioning --bucket <name> --versioning-configuration Status=Enabled` |
| S3.5 | Default encryption | Enable SSE-KMS | `aws s3api put-bucket-encryption --bucket <name> --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"<key-id>"}}]}'` |
| S3.6 | Public read ACL | Remove public ACL + enable BPA | `aws s3api put-bucket-acl --bucket <name> --acl private` + BPA |
| S3.8 | SSL requests only | Deny non-SSL in bucket policy | Deny with `aws:SecureTransport: false` |
| IAM.1 | Admin policy attached | Replace with scoped policy | Scope down via CloudTrail-derived least-privilege |
| IAM.3 | Access Analyzer | Enable IAM Access Analyzer | `aws accessanalyzer create-analyzer --analyzer-name org-analyzer --type ORGANIZATION` |
| IAM.4 | Access key age < 90d | Rotate or deactivate old keys | `aws iam update-access-key --access-key-id <key> --status Inactive` |
| IAM.5 | MFA for IAM users | Enable MFA for all console users | `aws iam create-virtual-mfa-device --virtual-mfa-device-name <name>` |
| IAM.7 | Password policy | Set account password policy | `aws iam update-account-password-policy --minimum-password-length 14 --require-symbols --require-numbers --require-uppercase-characters --require-lowercase-characters --max-password-age 90 --password-reuse-prevention 24` |
| IAM.8 | Unused credentials < 45d | Deactivate unused keys | `aws iam update-access-key --status Inactive` |
| CloudTrail.1 | Trail enabled | Create org-level trail | `aws cloudtrail create-trail --name org-trail --s3-bucket-name <bucket> --is-organization-trail` |
| CloudTrail.2 | Log file validation | Enable validation | `aws cloudtrail update-trail --name <trail> --enable-log-file-validation` |
| CloudTrail.4 | Log encryption (KMS) | Apply KMS CMK to trail | `aws cloudtrail update-trail --name <trail> --kms-key-id <key-arn>` |
| Config.1 | Config enabled all regions | Enable Config recorder | `aws configservice put-configuration-recorder ...` |
| EC2.2 | Default SG restricts traffic | Remove all rules from default SG | `aws ec2 revoke-security-group-ingress --group-id <sg> ...` |
| EC2.4 | EBS snapshot encryption | Enable EBS default encryption | `aws ec2 enable-ebs-encryption-by-default` |
| EC2.6 | VPC flow logs | Enable flow logs for all VPCs | `aws ec2 create-flow-logs --resource-type VPC --resource-ids <vpc-id> --traffic-type ALL --log-group-name <lg>` |
| EC2.15 | SG 0.0.0.0/0 admin port | Restrict SSH/RDP to known CIDR | `aws ec2 revoke-security-group-ingress --group-id <sg> --ip-permissions ...` |
| KMS.1 | KMS key rotation | Enable annual key rotation | `aws kms enable-key-rotation --key-id <key-id>` |
| KMS.2 | KMS key policy not wildcard | Restrict key policy principals | Edit key policy JSON |
| RDS.1 | RDS encryption | Enable encryption at rest | Snapshot → copy with encryption → restore |
| RDS.6 | Enhanced Monitoring | Enable Enhanced Monitoring | `aws rds modify-db-instance --db-instance-identifier <id> --monitoring-interval 60 --monitoring-role-arn <arn>` |
| Lambda.1 | Lambda IAM role check | Ensure dedicated scoped role | `aws lambda update-function-configuration --function-name <name> --role <role-arn>` |
| Lambda.2 | Lambda in VPC | Connect Lambda to VPC | `aws lambda update-function-configuration --vpc-config SubnetIds=...,SecurityGroupIds=...` |

### CIS AWS Foundations Benchmark (v1.2.0 / v1.4.0 / v2.0.0)

| CIS Control | Title | Fix Action |
|---|---|---|
| 1.1 | Avoid root account use | Create IAM admin user; do not use root for daily ops |
| 1.2 | MFA on root | Enable hardware MFA on root (virtual is insufficient for CIS) |
| 1.3 | Credentials unused >90d removed | Deactivate keys; delete inactive users |
| 1.4 | Access keys <90 days | Rotate access keys |
| 1.5 | Password policy | `aws iam update-account-password-policy` (min 14 chars) |
| 1.6 | Hardware MFA for root | Same as CIS 1.2 |
| 1.7 | Password expiry <90d | `--max-password-age 90` |
| 1.8 | Password reuse prevention | `--password-reuse-prevention 24` |
| 1.9 | No password policy | Create one (combines 1.5-1.8) |
| 1.10-1.12 | MFA for all IAM users | Enable MFA for every console user |
| 1.13-1.16 | No excessive access keys | Max 1 key per user; rotate inactive |
| 1.20 | IAM Access Analyzer | Enable (maps to FSBP IAM.3) |
| 1.21 | IAM credential report | `aws iam get-credential-report` monthly |
| 2.1 | CloudTrail enabled | Multi-region trail (maps to FSBP CloudTrail.1) |
| 2.2 | Log validation | Enable (maps to FSBP CloudTrail.2) |
| 2.3 | S3 bucket access logging | Enable server access logging on CloudTrail bucket |
| 2.4 | CloudTrail to CW Logs | `aws cloudtrail update-trail` + subscription filter |
| 2.5 | Config enabled | Maps to FSBP Config.1 |
| 2.6 | S3 bucket MFA delete | `aws s3api put-bucket-versioning --file mfa.json` (requires root) |
| 2.7-2.9 | CloudTrail logs encrypted | KMS encryption on trail |
| 3.1-3.4 | Security Hub alerts on root/MFA/unauthorized | CW metric filter + alarm + SNS |
| 3.5-3.14 | Network security / SG | Restrict 0.0.0.0/0 (maps to FSBP EC2.15) |
| 4.1 | No SG 0.0.0.0/0 on port 22 | Restrict SSH |
| 4.2 | No SG 0.0.0.0/0 on port 3389 | Restrict RDP |

### PCI-DSS v3.2.1 and NIST SP 800-53 Rev. 5

PCI controls (`PCI.EC2.1`, `PCI.IAM.1`, `PCI.S3.1`) and NIST controls
(`NIST.800-53.r5.*`) share the same underlying Config rules as FSBP. Map by
resource type + issue, not by the control ID prefix. The fix actions are
identical.

**Cross-standard deduplication:** The same resource may have 3-4 findings for
the same underlying issue. The fix is the same — apply once, all findings
re-evaluate independently.

## Multi-account aggregation (Organizations)

In an Organizations deployment with a delegated Security Hub administrator:

- Findings from **all member accounts** aggregate to the administrator
  account. `AwsAccountId` identifies the owning member account.
- A finding in a member account may be invisible if the member has not enabled
  Security Hub or accepted the administrator invitation.
- **Enrolled-but-not-enabled:** If a member account is enrolled but has
  Security Hub disabled, its controls show `NOT_AVAILABLE` with
  `SECURITY_HUB_NOT_ENABLED_IN_REGION`. This is a **WARNING** — the account
  SHOULD be monitored but is not.
- **Cross-region aggregation:** Security Hub supports cross-region aggregation
  via `FindingAggregator`. Findings from member regions appear with their
  original `Region` field but are visible in the aggregation region (~5 minute
  propagation delay).

When producing an aggregate report, group by `AwsAccountId` and report the
worst verdict per account.

**Cross-account role assumption failures (expert edge case):** When the
delegated administrator account cannot assume the service-linked role in a
member account (due to SCP, permissions boundary, or a broken trust policy),
controls for that member show `NOT_AVAILABLE` with `ASSUME_ROLE_ERROR`. This
is a WARNING, not NOT_APPLICABLE. The root cause is a role-trust
misconfiguration: verify the member account's
`AWSServiceRoleForSecurityHub` role exists and its trust policy allows
`securityhub.amazonaws.com`. In Organizations, this role is auto-created on
Security Hub enablement — if it is missing, the account was enrolled without
enabling Hub. Fix: enable Security Hub in the member account, which recreates
the role.

## Custom controls and non-standard findings

Security Hub supports **custom standards** and **custom controls** via
`CreateStandardsControl` or Config-backed custom rules. These appear with a
customer-defined `GeneratorId` that does not match FSBP / CIS / PCI / NIST ARN
patterns. The verdict logic is identical (Steps 0-8), but the fix action
requires a different lookup:

1. Check `Description` and `RemediationUrl` — set by the control author.
2. If absent, check `Remediation.Recommendation.Text` and `.Url` (ASFF
   per-finding remediation fields).
3. If neither present, map by `Resources[].Type`: identify the service, check
   the control title for keywords ("encryption", "public", "MFA"), and derive
   the fix from best practice. Cite "Custom control — derived remediation"
   and flag for human validation.

**Automation rules (formerly ingestion filters):** Security Hub supports
automation rules that can auto-update workflow status or even archive findings
on ingest. A finding that arrives as `SUPPRESSED` or `ARCHIVED` may have been
modified by an automation rule before you see it. Check
`UpdatedAt` vs `CreatedAt` — if `UpdatedAt` is seconds after `CreatedAt`, an
automation rule touched it. Use `aws securityhub list-automation-rules` to
audit active rules.

## Output format — worked examples

### Multi-finding report

```text
CONTROL: S3.2 (S3 Bucket-Level Public Access Prohibition)
VERDICT: FAILED
REASON: Rule 5 (active FAILED) — Compliance.Status is FAILED,
Workflow.Status is NEW, RecordState is ACTIVE. Bucket app-uploads-prod
does not have bucket-level BPA enabled.
SEVERITY: HIGH
REMEDIATION: Enable all 4 bucket-level BPA settings on app-uploads-prod:
aws s3api put-public-access-block --bucket app-uploads-prod
  --public-access-block-configuration
    BlockPublicAcls=true,IgnorePublicAcls=true,
    BlockPublicPolicy=true,RestrictPublicBuckets=true

CONTROL: IAM.7 (IAM Password Policy)
VERDICT: PASSED
REASON: Rule 7 (PASSED) — Compliance.Status is PASSED, RecordState is ACTIVE.
Password policy meets all FSBP requirements.
SEVERITY: MEDIUM
REMEDIATION: None required — control is compliant.

CONTROL: Redshift.1 (Redshift Clusters Public Access)
VERDICT: NOT_APPLICABLE
REASON: Rule 4 (NOT_AVAILABLE — NO_RESOURCES) — Compliance.Status is
NOT_AVAILABLE with StatusReasons code NO_RESOURCES. No Redshift clusters
exist in this account/region.
SEVERITY: MEDIUM
REMEDIATION: None required — control does not apply.

CONTROL: Config.1 (AWS Config Enabled)
VERDICT: WARNING
REASON: Rule 4 (NOT_AVAILABLE — SUPPORTED_SERVICE_NOT_ENABLED) —
Compliance.Status is NOT_AVAILABLE with StatusReasons code
SUPPORTED_SERVICE_NOT_ENABLED. AWS Config is not enabled in eu-west-2,
so this control cannot evaluate. This is a monitoring gap, not a pass.
SEVERITY: MEDIUM
REMEDIATION: Enable AWS Config in eu-west-2:
aws configservice put-configuration-recorder
  --configuration-recorder name=default,roleARN=<role>
  --recording-group allSupported=true,includeGlobalResourceTypes=true
```

## NEVER (anti-patterns)

- NEVER pass through `Compliance.Status = NOT_AVAILABLE` as NOT_APPLICABLE
  without checking `StatusReasons`. `NO_RESOURCES` means the control does not
  apply (NOT_APPLICABLE), but `SUPPORTED_SERVICE_NOT_ENABLED` means Config is
  off — a monitoring posture gap that is a WARNING. Treating the latter as
  NOT_APPLICABLE hides a misconfiguration that makes the entire compliance
  posture unreliable.

- NEVER treat a SUPPRESSED finding as PASSED. `Workflow.Status = SUPPRESSED`
  means someone hid the finding from the default view. If
  `Compliance.Status = FAILED`, the control is still failing — the verdict is
  WARNING. Suppression is a triage decision, not a remediation.

- NEVER treat `Workflow.Status = RESOLVED` as evidence that the resource is
  now compliant. RESOLVED is an operator assertion. Security Hub re-evaluates
  on its own schedule. If still `FAILED` after 48h (or 1h for config-change
  controls), the fix failed.

- NEVER classify an ARCHIVED finding as FAILED. `RecordState = ARCHIVED` means
  the resource was deleted or the control superseded. The verdict is
  NOT_APPLICABLE.

- NEVER ignore `FirstObservedAt` / `UpdatedAt` timestamps. A `FAILED` finding
  open for 180 days is a different operational concern than one opened
  yesterday. Age compounds risk — escalate for findings > 90 days old.

- NEVER classify an integration finding (GuardDuty, Inspector, Macie,
  Detective, Firewall Manager) as a control compliance verdict. These lack a
  `Compliance` block — they are security events. Route them to the
  appropriate detector skill.

- NEVER assume a single region's findings represent global compliance.
  Security Hub is regional. A finding for `us-east-1` says nothing about
  `eu-west-1`. Always check the `Region` field. In multi-region accounts, the
  delegated administrator must aggregate via `FindingAggregator`.

- NEVER recommend disabling a Security Hub control as the fix for a FAILED
  finding. Disabling removes visibility — it trades FAILED for
  NOT_APPLICABLE without fixing the resource. The only legitimate reason to
  disable is a confirmed false-positive.

- NEVER aggregate findings by severity alone without considering blast radius.
  A `MEDIUM` FAILED on an IAM role with cross-account trust is more dangerous
  than ten `HIGH` findings on isolated dev resources.

- NEVER assume `Severity.Label` is the final priority. The aggregate (N > 10)
  and time-decay (> 90 days) escalation rules override the label — a `MEDIUM`
  FAILED on 50 resources for 6 months is effectively P1.

- NEVER batch-update finding workflow status to RESOLVED without confirming
  the resource is actually fixed. If the resource is still non-compliant,
  Security Hub re-opens the finding on the next cycle.

- NEVER trust ARN fields blindly. A finding `Resources[].Id` that does not
  match the AWS ARN pattern
  (`arn:aws:[service]:[region]:[account]:[resource]`) indicates either a
  malformed ASFF payload or a non-AWS resource incorrectly ingested. Flag
  the data-quality issue and verify the finding source before acting on the
  remediation. Malformed ARNs cause downstream failures in any CLI command
  that takes `--resource-arn` or `--bucket` parameters.

- NEVER assume cross-account Security Hub findings are actionable from the
  administrator account. The delegated administrator can SEE findings from
  member accounts but may not have permission to MODIFY the underlying
  resources. A control backed by a Config rule that assumes
  `AWSServiceRoleForSecurityHub` in the member account will show
  `ASSUME_ROLE_ERROR` if that role's trust policy is broken or the member
  account was enrolled without enabling Security Hub. This is a WARNING — the
  role trust must be fixed before the control can evaluate.

- NEVER call `BatchUpdateFindings` with more than 100 finding identifiers.
  The API rejects batches over 100 with `InvalidInputException`. Chunk into
  groups of 100 or fewer.

- NEVER apply remediation commands in a tight loop without exponential
  backoff. Config rule evaluations and Security Hub API calls share a rate
  limit. A burst across 50 resources can trigger `ThrottlingException` and
  leave some unremediated silently.

- NEVER attempt to update `Compliance.Status` via `BatchUpdateFindings` — it
  is a system-managed field. Only `Workflow.Status`, `RecordState`, `Note`,
  and `Severity` are user-updatable. Trying to set `Compliance.Status`
  returns `InvalidInputException`.

## API and CLI constraints

**Security Hub API limits:**
- `GetFindings` returns **max 100 findings per page**. Use `--next-token` for
  pagination. Large accounts require multiple paginated calls.
- `BatchUpdateFindings` accepts **max 100 finding identifiers per call**.
  The `Note` field has a **4 KB limit** — truncate verbose justifications.
- `GetEnabledStandards` and `BatchGetStandardsControlAssociations` have lower
  throughput limits — cache the standards list.
- Updates via `BatchUpdateFindings` are **eventually consistent** (~30 seconds
  to reflect in `GetFindings`). Do not re-query immediately after an update
  expecting instant visibility.

**Throttling and retry:**
- Security Hub API calls are subject to **rate limiting** (token bucket).
  On `ThrottlingException`, use exponential backoff (`--retry-mode adaptive`
  on the CLI, or boto3 `botocore.config.Config` with `retry_mode='adaptive'`).
- Config rule evaluations also throttle under heavy load.

**CLI failure recovery:**
- `batch-update-findings` fails with `InvalidInputException` → finding
  identifier is malformed or the finding no longer exists. Skip and continue.
- Remediation fails with `AccessDenied` → verify caller has service-level
  permission AND no SCP or permissions boundary is blocking. Security Hub
  findings do not check SCPs — a finding can report a state the caller cannot
  modify.
- `aws s3api put-public-access-block` fails with `NoSuchBucket` → bucket was
  deleted between finding and remediation. Mark finding ARCHIVED.

## Pre-flight safety checks (run before any remediation)

**Dry-run mode (REQUIRED for batch remediation of >5 resources):** Before
applying any fix in bulk, run an audit-only pass:
1. For CLI commands with native `--dry-run` support (e.g., `aws iam
   simulate-principal-policy`, `aws s3api put-bucket-policy --dry-run`):
   run with `--dry-run` and inspect the output for side-effects.
2. For commands without native dry-run (e.g., `put-public-access-block`,
   `enable-key-rotation`): emit the exact command to stdout prefixed with
   `# DRY-RUN:` and HALT. Require explicit user confirmation
   (`--confirm-execute` flag or interactive "yes") before re-running without
   the prefix.
3. For BatchUpdateFindings: first run with `--note "DRY-RUN: would set
   RESOLVED"` but WITHOUT `--workflow Status=RESOLVED`. Verify the note
   appears, then run the real update.
4. Batch dry-run output must include: the command, the target resource ARN,
   the current state (from pre-flight capture), and the expected post-fix
   state. This allows rollback planning before any state change.

- **Confirm the resource still exists** before applying a fix. A finding may
  reference a deleted resource (Security Hub can lag by up to 24h):
  - S3: `aws s3api head-bucket --bucket <name>`
  - IAM: `aws iam get-role --role-name <name>`
  - EC2: `aws ec2 describe-security-groups --group-ids <sg-id>`
  - CloudTrail: `aws cloudtrail describe-trails --trail-name-list <name>`
  If the resource does not exist, update the finding to ARCHIVED.

- **Capture current state for rollback** before modifying any resource:
  - S3 bucket policy: `aws s3api get-bucket-policy --bucket <name> > backup.json`
  - IAM policy: `aws iam get-policy-version --policy-arn <arn> > backup.json`
  - Security group: `aws ec2 describe-security-groups --group-ids <sg> > backup.json`
  Prefer additive changes (enable BPA) over destructive changes (delete
  policy).

- **Confirm the finding is for the current account/region.** Security Hub
  findings are region-scoped. Verify `--region` matches the finding's `Region`
  field.

- **Verify the delegated administrator scope.** If operating from a member
  account, you may not have permissions to modify resources in another member.
  Check `AwsAccountId`.

- **For CRITICAL findings on trust-boundary resources** (cross-account IAM
  roles, public S3 buckets, KMS keys with wildcard policies), treat as
  incident response — contain first (enable BPA, restrict trust policy), then
  investigate CloudTrail for evidence of exploitation during the exposure
  window.

- **Permission fallback:** if the caller receives `AccessDenied` on the
  remediation command, do NOT silently fail. Check for: (1) an SCP denying
  the action at the OU or account level, (2) a permissions boundary capping
  the role, (3) a service control policy from the management account. Document
  the blocker and escalate to the cloud governance team.

## Remediation guidance

### For FAILED findings

1. Identify the control ID and look up the fix action in the mapping table.
2. Run the pre-flight safety checks (confirm resource exists, capture state,
   dry-run if batch).
3. Apply the fix via the CLI command in the mapping table.
4. Update the finding workflow status to RESOLVED:
   `aws securityhub batch-update-findings --finding-identifiers
   Id=<id>,ProductArn=<arn> --workflow Status=RESOLVED --note "Applied
   <fix-action>, awaiting re-evaluation."`
5. Wait for the next evaluation cycle (12-24h for periodic, 5-30 min for
   config-change). If the finding auto-updates to `PASSED`, remediation is
   confirmed. If still `FAILED` after 48h, re-investigate the resource.
6. For cross-standard duplicates, apply the fix once — all findings
   re-evaluate independently.

### For WARNING findings

- **Suppressed FAILED:** Review the suppression justification. If the
  compensating control is still valid, document it in a compliance exception
  register. If stale (no note, > 90 days), unsuppress:
  `aws securityhub batch-update-findings --workflow Status NEW`. If the
  control now passes, auto-close; if still failing, proceed to the FAILED
  remediation path.
- **Resolved-pending:** If > 48h since resolution and still FAILED,
  re-investigate the resource. If < 48h, wait for the next cycle.
- **NOT_AVAILABLE (Config gap):** Enable AWS Config in the affected region.

### For NOT_APPLICABLE findings

- **NO_RESOURCES / DISABLED_CONTROL:** No action. Document that the control
  does not apply to this account's resource profile.
- **Integration findings:** Route to the appropriate detector skill.

## Recent AWS features (2024-2026)

- **Security Hub central configuration (2024-2025):** Security Hub now supports central configuration management across an Organization, enabling consistent standard enablement and control configuration from the delegated administrator account. Auditors should verify that the central configuration policy is deployed and that member accounts have not locally overridden critical controls.
- **Automated Security Response on AWS (2024):** The ASR solution provides pre-built EventBridge-to-SSM remediation playbooks for Security Hub findings. Auditors should verify that ASR playbooks are deployed for critical controls and that the SSM automation documents have scoped IAM roles.
- **Control lifecycle updates (2024-2025):** Security Hub periodically updates control specifications and adds new controls. Auditors should verify that newly released controls are evaluated and that disabled controls are documented with justification.
- **Security Hub integration with Audit Manager (2024):** Enhanced integration allowing Security Hub findings to feed Audit Manager evidence collection. Auditors should verify that the integration is configured for compliance frameworks that require evidence of continuous monitoring.

## Domain

AWS CloudOps / Security Hub Compliance & Posture Management.

## AWS documentation

- **AWS Security Hub User Guide** — https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html
- **Security Hub Security** — https://docs.aws.amazon.com/securityhub/latest/userguide/security.html
- **Security Hub API Reference** — https://docs.aws.amazon.com/securityhub/1.0/APIReference/
- **Security Hub CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/securityhub/
- **Central configuration** — https://docs.aws.amazon.com/securityhub/latest/userguide/central-configuration.html
