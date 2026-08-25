# Advanced Patterns — Security Hub Control-Compliance Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

### Step 0 — schema version check

**Schema version check:** Verify `SchemaVersion = 2018-10-08` (the only ASFF
version). If older or missing, flag it — `Compliance.StatusReasons` was added
to the schema in late 2020, so findings created before that may lack
StatusReasons even on NOT_AVAILABLE. Append a note: "Pre-2020 schema —
StatusReasons may be absent."

### Step 0 — malformed ARN DATA_QUALITY flag

```
DATA_QUALITY: Finding Id / Resource Id does not match expected ARN format.
Verify the source integration is producing valid ASFF.
```
This does not change the verdict — it is a data-quality flag.

### Step 0 — unexpected enum values

**Unexpected enum values:** If `Compliance.Status` is not one of
`PASSED | WARNING | FAILED | NOT_AVAILABLE`, emit WARNING with:
"Unrecognized Compliance.Status `<value>` — not a valid ASFF enum. Triage
manually." Do NOT guess the intent.

### Step 0 — field-defaulting rules

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

### Step 1 — freshness guard

**Freshness guard:** even if `RecordState = ACTIVE`, check `UpdatedAt`. If the
finding has not been updated in > 30 days, the Security Hub service may have
stopped refreshing (account removed from delegated admin, control disabled
and re-enabled). Append:
```
STALE_FLAG: Finding last updated <date> (>30 days ago). Verify the control is
still enabled and Security Hub is refreshing in this region.
```

### Step 1 — deprecated-standard edge case

**Deprecated-standard edge case (expert):** When a standard version is
deprecated (e.g., CIS v1.2.0 → v2.0.0 migration in Q4 2024), existing
findings for the old standard's controls show as ARCHIVED but may persist in
the datastore for 90 days. These are NOT current failures — classify as
NOT_APPLICABLE with note "control belongs to deprecated standard version."

### Step 2 — suppression lifecycle heuristic

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

### Step 3 — config-change vs periodic controls

**Config-change vs periodic controls (expert distinction):** The 48h
threshold is conservative. Config-change-triggered controls re-evaluate within
5-30 minutes of a resource change. If a config-change control is still FAILED
1 hour after RESOLVED was marked, the fix already failed — do not wait 48h.
For periodic controls (CloudTrail, Config, IAM password policy), the full 24h
window is needed. The 48h global threshold covers the worst case.

## Step 4 — full StatusReason code reference

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

## Recent AWS features (2024-2026)

- **Security Hub central configuration (2024-2025):** Security Hub now supports central configuration management across an Organization, enabling consistent standard enablement and control configuration from the delegated administrator account. Auditors should verify that the central configuration policy is deployed and that member accounts have not locally overridden critical controls.
- **Automated Security Response on AWS (2024):** The ASR solution provides pre-built EventBridge-to-SSM remediation playbooks for Security Hub findings. Auditors should verify that ASR playbooks are deployed for critical controls and that the SSM automation documents have scoped IAM roles.
- **Control lifecycle updates (2024-2025):** Security Hub periodically updates control specifications and adds new controls. Auditors should verify that newly released controls are evaluated and that disabled controls are documented with justification.
- **Security Hub integration with Audit Manager (2024):** Enhanced integration allowing Security Hub findings to feed Audit Manager evidence collection. Auditors should verify that the integration is configured for compliance frameworks that require evidence of continuous monitoring.

