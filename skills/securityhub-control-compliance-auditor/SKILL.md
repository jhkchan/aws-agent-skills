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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#activation).
> Four ASFF detection signals and the do-NOT-invoke exclusions (CloudTrail events, bare IAM policy JSON, Audit Manager, Config compliance JSON).

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset).
> Four overlapping finding states, read in dashboard-triage order, reflect current real-world posture rather than the raw status string.

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

> Moved to [references/error-handling.md](references/error-handling.md#step-0--malformed-json-error-emit-block).
> WARNING emit template for unparseable finding JSON (GetFindings re-fetch, support case for the source integration).

**Missing Compliance block:** If the `Compliance` key is absent entirely,
the finding is an **integration finding** (GuardDuty, Inspector, Macie,
Detective, Firewall Manager) or a custom product finding. It is a security
event, not a control compliance evaluation:

> Moved to [references/error-handling.md](references/error-handling.md#step-0--missing-compliance-block-emit).
> NOT_APPLICABLE emit template for integration findings (GuardDuty, Inspector, Macie, Detective, Firewall Manager) and custom products.


**Malformed ARN fields:** If the finding `Id` or `Resources[].Id` does not
match the AWS ARN pattern
`arn:aws:[a-z0-9-]+:[a-z]{2}-[a-z]+-\d:\d{12}:.*`, append:

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0--malformed-arn-data_quality-flag).
> DATA_QUALITY flag for finding Id / Resources[].Id not matching the AWS ARN pattern (does not change the verdict).


**Field-defaulting rules (apply when a field is absent but non-fatal):**

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0--field-defaulting-rules).
> Defaults: StatusReasons-missing-on-NOT_AVAILABLE → WARNING (never NOT_APPLICABLE), RecordState → ACTIVE, Workflow → NEW, UpdatedAt-absent → STALE_FLAG, Severity → MEDIUM.

### Step 1 — RecordState = ARCHIVED → NOT_APPLICABLE (stale)

Security Hub archives findings when the resource was deleted, the control was
disabled, or the finding was superseded by a newer one. An archived finding
represents a **historical** state. If `RecordState = ARCHIVED`, emit
**NOT_APPLICABLE** regardless of `Compliance.Status`.

Cite "Rule 1: archived — resource deleted or control superseded".


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-1--freshness-guard).
> STALE_FLAG when UpdatedAt is >30 days old even on ACTIVE findings (delegated-admin removal, control re-enable).


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


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-2--suppression-lifecycle-heuristic).
> No suppression TTL — validity heuristic by age and Note presence (<30d valid, 30-90d review, >90d stale, no-Note suspect).

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


> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-4--full-statusreason-code-reference).
> Complete StatusReason code → verdict → meaning table (NO_RESOURCES through UNKNOWN_CONTROL_STATUS).

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#severity-escalation-matrix).
> Verdict × severity priority/SLA table, cross-standard severity rule, and blast-radius escalation (aggregate N>10, time-decay >90d, trust-boundary → P0).

## Config-rule evaluation triggers (expert reference)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#config-rule-evaluation-triggers-expert-reference).
> Config-change vs periodic trigger families per control, 5-30 min vs 6-24h re-evaluation windows, describe-config-rules verification.

## Security Hub internals (non-obvious operational knowledge)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#security-hub-internals-non-obvious-operational-knowledge).
> Dedup composite key, BatchUpdateFindings race, Config backlog delays, ingestion latency stages, automation-rule silent suppression, control enablement cost model.

## Finding correlation and root-cause grouping

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#finding-correlation-and-root-cause-grouping).
> Root-cause grouping rules (S3 BPA fan-in, account-policy gaps, Config-disabled clusters, cross-standard duplicates).

## Coverage assessment heuristic

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#coverage-assessment-heuristic).
> coverage_score formula and 90% / 70% operational benchmarks.

## Control-to-fix-action mapping

> Moved to [references/remediation-guidance.md](references/remediation-guidance.md#control-to-fix-action-mapping).
> FSBP (S3, IAM, CloudTrail, Config, EC2, KMS, RDS, Lambda), CIS v1.2-v2.0, and PCI/NIST control → fix action → CLI tables.

## Multi-account aggregation (Organizations)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#multi-account-aggregation-organizations).
> Delegated-admin aggregation, enrolled-but-not-enabled WARNING, FindingAggregator cross-region propagation, ASSUME_ROLE_ERROR root cause and fix.

## Custom controls and non-standard findings

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#custom-controls-and-non-standard-findings).
> Custom control remediation lookup chain (Description/RemediationUrl → ASFF Remediation fields → resource-type derivation) and automation-rule detection.

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

> Moved to [references/error-handling.md](references/error-handling.md#api-and-cli-constraints).
> Pagination and batch limits (100 findings, 4 KB Note), throttling/backoff, eventual consistency, CLI failure recovery (InvalidInputException, AccessDenied, NoSuchBucket).

## Pre-flight safety checks (run before any remediation)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-safety-checks-run-before-any-remediation).
> Dry-run mode for batch remediation, resource-existence probes per service, rollback state capture, region/delegated-admin verification, trust-boundary incident handling, permission-fallback escalation.

## Remediation guidance

> Moved to [references/remediation-guidance.md](references/remediation-guidance.md#remediation-guidance).
> FAILED playbook (map → pre-flight → fix → RESOLVED → await re-evaluation), WARNING playbook (suppression review/unsuppress, resolved-pending, Config gap), NOT_APPLICABLE disposition.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> Central configuration, Automated Security Response on AWS, control lifecycle updates, Audit Manager integration.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Activation triggers, Mindset, Step 0-4 detail prose, severity escalation matrix, Config-rule triggers, Security Hub internals, correlation, coverage heuristic, multi-account aggregation, custom controls, recent AWS features
- [diagnostic-commands](references/diagnostic-commands.md) — pre-flight safety checks (dry-run, existence probes, rollback capture)
- [error-handling](references/error-handling.md) — malformed-input emit blocks and API/CLI constraints with failure recovery
- [remediation-guidance](references/remediation-guidance.md) — control-to-fix-action mapping tables and per-verdict remediation playbooks

## Domain

AWS CloudOps / Security Hub Compliance & Posture Management.

## AWS documentation

- **AWS Security Hub User Guide** — https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html
- **Security Hub Security** — https://docs.aws.amazon.com/securityhub/latest/userguide/security.html
- **Security Hub API Reference** — https://docs.aws.amazon.com/securityhub/1.0/APIReference/
- **Security Hub CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/securityhub/
- **Central configuration** — https://docs.aws.amazon.com/securityhub/latest/userguide/central-configuration.html
