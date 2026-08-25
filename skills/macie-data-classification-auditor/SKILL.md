---
name: macie-data-classification-auditor
description: Audits Amazon Macie data-classification posture — classification job coverage and status, automated sensitive data discovery (ASDD) enablement, sensitive data finding triage state (PII / credentials / financial), custom data identifiers, bucket_allow_list scope, findings auto-archive filters, and Security Hub export integration. Emits a deterministic verdict (NO_CLASSIFICATION | UNTRIAGED_FINDINGS | CONFIG_GAP | OK) per account scope with enumerated findings and specific CLI remediation. Use when reviewing Macie classification coverage, triaging sensitive data discoveries, validating allow-list scope, checking Security Hub integration, or auditing sensitive-data discovery posture before a compliance review.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline posture classification. Live- account audits use aws macie2 get-macie-session, list-classification-jobs, list-findings, get-findings, list-allow-lists, and describe-organization- configuration (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: NO_CLASSIFICATION | UNTRIAGED_FINDINGS | CONFIG_GAP | OK
  when_to_use: Reviewing Macie classification coverage before a compliance audit, triaging sensitive data findings (PII, credentials, financial), validating bucket_allow_list scope, checking Security Hub export integration, auditing automated sensitive data discovery posture, or verifying that classification jobs are running and producing results.
  activation_triggers: audit macie classification, check macie findings, are there untriaged macie findings, is sensitive data discovery enabled, macie allow list too broad, macie security hub export, macie classification job failed, sensitive data in s3, pii audit macie, macie posture check
  invocation_schema: 'Input: either (a) a Macie posture snapshot (session status, ASDD config, classification jobs, findings summary, allow list, Security Hub integration), OR (b) an account / region for live-account audit. Output: deterministic ACCOUNT / VERDICT / REASON / FINDINGS / REMEDIATION block per account scope, where VERDICT belongs to {NO_CLASSIFICATION, UNTRIAGED_FINDINGS, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Macie, data classification, sensitive data, PII, credentials, financial data, classification job, automated discovery, ASDD, allow list, findings triage, Security Hub, custom data identifier, data loss prevention, DLP, compliance, S3 data security, sensitive data discovery
  tags: macie, security, data-classification, pii, sensitive-data, dlp, compliance, audit
---

# Macie Data Classification Auditor

## Quick-start

1. **Scanning?** Session ENABLED + at least one active job (RUNNING/COMPLETE)
   or ASDD ENABLED. If neither → **NO_CLASSIFICATION**.
2. **Triaged?** Zero open (`archived: false`) HIGH-severity findings. If
   any exist → **UNTRIAGED_FINDINGS**.
3. **Plumbing?** Security Hub export on, allow-list scoped (no wildcards),
   no active auto-archive filter, ASDD fresh (<48h). If any gap →
   **CONFIG_GAP**.
4. **All pass?** → **OK**.

Deep Macie behaviors, edge cases, and non-obvious failure modes are in
the [Reference — Expert knowledge](#reference--expert-knowledge--non-obvious-macie-behaviors)
section at the end.

## Mindset

**One-line takeaway:** the verdict flows from coverage to action to
configuration — you must be scanning (Step 1), you must have triaged what
was found (Step 2), and the plumbing must deliver findings to operators
(Step 3). Skip a step and the downstream verdict is unreliable.

Amazon Macie is the only AWS-native service that automatically discovers
sensitive data (PII, credentials, financial data) in S3. A Macie posture
gap means you are either **blind** (no scanning), **aware but inactive**
(untriaged findings), or **mis-configured** (findings not flowing to the
SOC). The worst state is NO_CLASSIFICATION because you have zero
visibility — you do not even know what you do not know.

## Quick reference — verdict thresholds and output format

**MANDATORY output format — always emit in this exact ALL CAPS structure:**

```text
ACCOUNT: <account-scope-id> (<region>)
VERDICT: NO_CLASSIFICATION | UNTRIAGED_FINDINGS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and finding>
FINDINGS:
  - [NO_CLASSIFICATION] <description (Step Na)>
  - [CONFIG_GAP] <description (Step Nb)>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

The account-scope-id is the identifier from the input (e.g., the scope
label). The VERDICT value must be exactly one of the four values above,
in ALL CAPS with underscores. Field names (ACCOUNT, VERDICT, REASON,
FINDINGS, REMEDIATION) must be ALL CAPS.

| Condition | Verdict | Step |
|---|---|---|
| No active classification jobs AND ASDD disabled | **NO_CLASSIFICATION** | 1 |
| All jobs in FAILED / CANCELLED / USER_CANCELLED AND ASDD disabled | **NO_CLASSIFICATION** | 1 |
| Active coverage AND open (non-archived) HIGH-severity findings | **UNTRIAGED_FINDINGS** | 2 |
| Active coverage, findings triaged, but Security Hub export disabled | **CONFIG_GAP** | 3a |
| Active coverage, findings triaged, but allow-list has wildcard prefixes | **CONFIG_GAP** | 3b |
| Active coverage, findings triaged, but auto-archive filter active | **CONFIG_GAP** | 3c |
| Active coverage, findings triaged, but ASDD lastRunTime stale >48h | **CONFIG_GAP** | 3d |
| All dimensions pass | **OK** | 4 |

See the ordered steps below for edge cases. Deep Macie scanning internals
are in the [Expert knowledge](#step-0-expert-knowledge--non-obvious-macie-behaviors)
section.

## Pre-flight: account / session gate

Before evaluating the Macie posture, verify the account state. Several
attributes short-circuit the audit.

| Attribute | Value | Effect on audit |
|---|---|---|
| `macieSession.status` | `ENABLED` | Proceed with full audit. |
| `macieSession.status` | `PAUSED` | Macie is administratively paused — no scanning, no new findings. Treat as NO_CLASSIFICATION. |
| `macieSession.status` | `DISABLED` / absent | Macie is not enabled. Verdict: **NO_CLASSIFICATION**. |
| `organizationConfig` | delegated admin set | This is the Macie admin account — findings for all member accounts aggregate here. Audit at org scope. |
| S3 buckets | zero buckets in account | No data to classify. Note as informational; do NOT emit NO_CLASSIFICATION (there is nothing to scan). |

**Multi-region note:** Macie is regional, not global. Each region has
independent session, jobs, findings, and configuration. A clean posture
in us-east-1 tells you nothing about ap-southeast-1. For live-account
audits, iterate `get-macie-session` per region and audit each separately.
If a region's snapshot is incomplete (missing session, jobs, or findings
fields), emit `VERDICT: ERROR` for that region only — do not let one
region's missing data invalidate the audit of other regions.

> The pagination guidance and the AccessDeniedException handling moved verbatim to [references/error-handling.md](references/error-handling.md).
> Load it when Macie API calls fail or results paginate.

**If the posture snapshot is malformed** (missing required fields:
session status, job list, or findings summary), output:

```text
ACCOUNT: <account-id>
VERDICT: ERROR
REASON: Macie posture snapshot is incomplete — cannot classify.
REMEDIATION: Collect session, jobs, findings, allow-list, and Security Hub
integration data. See the live-account commands in the Remediation section.
```

## Process — Classification logic (apply in order, first match wins)

> **Expert knowledge:** non-obvious Macie behaviors that change verdicts
> (ASDD sampling, USER_CANCELLED partial results, initialRun blind spots,
> Security Hub non-retroactivity, cost traps) are documented in the
> [Reference — Expert knowledge](#reference--expert-knowledge--non-obvious-macie-behaviors)
> section at the end of this skill. Consult it when a verdict is
> borderline or an edge case is not covered by the steps below.

### Step 1: Classification coverage check (NO_CLASSIFICATION gate)

Determine whether Macie is actively scanning for sensitive data. This is
the highest-priority dimension because without coverage, every downstream
check is meaningless.

**Classification jobs:** enumerate all jobs. A job is **active** if its
`jobStatus` is `RUNNING` or `COMPLETE` AND it was created or last run
within the last 90 days. Jobs in `FAILED`, `CANCELLED`, or
`USER_CANCELLED` status are NOT active — they are not producing new
findings.

**ASDD:** check `automatedDiscoveryConfig.status`. If `ENABLED`, Macie
continuously samples S3 buckets for sensitive data (with the sampling
caveat above). If `DISABLED`, ASDD is off.

**Verdict logic:**
- If there are ZERO active classification jobs AND ASDD is DISABLED →
  **NO_CLASSIFICATION**. The account has no sensitive-data visibility.
- If ASDD is ENABLED, the account has at least sampling-level coverage.
  Proceed to Step 2. (Note the sampling caveat in findings.)

> This edge-case walkthrough moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it when a job exists but is not active.

### Step 2: Findings triage evaluation (UNTRIAGED_FINDINGS)

If Step 1 passed (active coverage exists), evaluate whether discovered
sensitive data has been triaged.

**Findings query:** list findings where `archived: false`. For each
finding, check `severity`:
- **HIGH** severity findings (credentials, SSN, credit card, private
  keys) that are NOT archived → untriaged exposure. These represent
  real sensitive data at rest that has not been addressed.
- **MEDIUM** severity findings (email, names, phone numbers) that are
  not archived → informational, not the verdict trigger.

**Verdict logic:**
- If there are one or more open (`archived: false`) findings with
  `severity: HIGH` → **UNTRIAGED_FINDINGS**. The account has visibility
  into sensitive data exposure but has not acted on it.
- If all findings are archived (triaged) or no findings exist → proceed
  to Step 3.

**Severity-by-category reference (managed data identifiers):**

| Category | Example identifiers | Typical severity |
|---|---|---|
| Credentials | `AWS_CREDENTIALS`, `PRIVATE_KEY`, `API_KEY` | **HIGH** |
| Financial | `CREDIT_CARD_NUMBER`, `BANK_ACCOUNT_NUMBER` | **HIGH** |
| National ID | `US_SOCIAL_SECURITY_NUMBER`, `UK_NATIONAL_INSURANCE_NUMBER`, `PASSPORT_NUMBER` | **HIGH** |
| Personal | `EMAIL_ADDRESS`, `PERSON_NAME`, `PHONE_NUMBER`, `PHYSICAL_ADDRESS` | **MEDIUM** |

### Step 3: Configuration gap analysis (CONFIG_GAP)

If coverage is active and findings are triaged (or none exist), check the
plumbing that keeps Macie effective.

**Step 3a — Security Hub export:** Check whether Macie is configured to
publish findings to Security Hub (`publishingStatus: ENABLED` or
`publishingDestinationConfig`). If disabled → **CONFIG_GAP**. Without
Security Hub export, findings only exist in Macie's own console. SOC
teams monitoring Security Hub have no visibility into sensitive data
discoveries. This is the most common Macie configuration gap.

**Step 3b — Allow-list scope:** Review each allow-list entry. If any
entry uses a wildcard prefix (e.g., `s3://bucket/*` or
`s3://bucket/logs/*`) → **CONFIG_GAP**. Wildcard prefixes mask entire
paths and can hide future sensitive data. The allow-list should use
specific object paths or object-level patterns, not prefix wildcards.

**Step 3c — Auto-archive findings filter:** Check for findings filters
with `action: ARCHIVE`. If any exist and are enabled → **CONFIG_GAP**.
Auto-archive filters suppress findings before operators see them. Each
filter should be reviewed to confirm it targets genuine false positives
only.

**Step 3d — ASDD staleness:** If ASDD is enabled, check
`lastRunTime`. If more than 48 hours in the past → **CONFIG_GAP**. A
stale ASDD indicates the discovery cycle is stalled (throttling, service
issue, or permission drift). Recent uploads are not being scanned.

**Verdict logic:** If any of Steps 3a-3d fails → **CONFIG_GAP**. Multiple
config gaps are all listed in the FINDINGS block.

### Step 4: OK

If coverage is active (Step 1), no untriaged HIGH findings (Step 2), and
all configuration checks pass (Step 3) → **OK**.

## Output format (per account scope)

```text
ACCOUNT: <account-id> (<region>)
VERDICT: NO_CLASSIFICATION | UNTRIAGED_FINDINGS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and finding>
FINDINGS:
  - [NO_CLASSIFICATION] <description (Step Na)>
  - [CONFIG_GAP] <description (Step Nb)>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

### Worked example — untriaged PII findings

```text
ACCOUNT: 333333333333 (us-east-1)
VERDICT: UNTRIAGED_FINDINGS
REASON: ASDD is enabled and the classification job completed, but 3 open
HIGH-severity findings (US_SOCIAL_SECURITY_NUMBER, CREDIT_CARD_NUMBER,
AWS_CREDENTIALS) have not been triaged (Step 2).
FINDINGS:
  - [UNTRIAGED_FINDINGS] 3 open HIGH findings: 2 SSN findings in
    s3://customer-data/exports/, 1 AWS credential finding in
    s3://app-config/secrets.json (Step 2)
  - [OK] ASDD enabled, classification job in COMPLETE status (Step 1)
  - [OK] Security Hub export enabled (Step 3a)
REMEDIATION:
  CONFIRM: About to rotate IAM access key and archive findings in account
  333333333333 (us-east-1). This affects the exposed credential and 3
  findings. Proceed? (yes/no)
  1. Immediately investigate the AWS credential finding — rotate the
     exposed key: aws iam list-access-keys --user-name <user>, then
     aws iam delete-access-key --access-key-id <AKIA...> --user-name <user>.
  2. Verify SSN findings: download the flagged objects and confirm the
     data. If real PII, move to an encrypted, access-restricted bucket.
  3. Archive each finding AFTER remediation:
     aws macie2 update-findings --finding-ids <id> --status ARCHIVED.
```

## Anti-Patterns — NEVER

- NEVER classify an account with ASDD disabled and no active jobs as
  anything other than NO_CLASSIFICATION. Without scanning, you have zero
  visibility into sensitive data — the worst possible posture. A
  "CONFIG_GAP" implies partial coverage; "no coverage" is not partial.

- NEVER treat a FAILED or CANCELLED classification job as "active
  coverage." A job that has been failing for weeks provides no new
  findings. Operators often assume "we have a Macie job" without checking
  its status. Verify `jobStatus` — only RUNNING and COMPLETE are active.

- NEVER treat `archived: true` as "remediated." Archiving is a
  bookkeeping action in Macie. The sensitive data is still in the S3
  bucket. An archived HIGH finding still represents real exposure. Only
  treat archived findings as triaged when accompanied by evidence of
  investigation or verified data removal.

- NEVER assume ASDD-enabled equals full coverage. ASDD uses probabilistic
  sampling — it does not scan every object. For compliance-driven audits
  (PCI-DSS, HIPAA), require a classification job with
  `samplingPercentage: 100`. ASDD alone may miss sensitive data in
  rarely-accessed objects.

- NEVER report a CONFIG_GAP verdict when there are open HIGH findings.
  UNTRIAGED_FINDINGS is higher priority than CONFIG_GAP — the actual
  sensitive data exposure takes precedence over a plumbing issue. Always
  evaluate Step 2 before Step 3.

- NEVER recommend deleting an allow-list entry without verifying why it
  was created. Allow-lists often suppress known false positives (e.g.,
  test data that looks like PII). Removing the entry may flood the
  findings queue with false positives. Recommend scoping the entry to a
  specific path instead of deleting it.

- NEVER enable ASDD or create a classification job without considering
  cost. Macie charges per GB scanned. A full scan of a 100 TB data lake
  can cost thousands of dollars. Recommend starting with a sampled
  classification job and expanding coverage based on findings.

- NEVER assume Macie is enabled across all regions. Macie is regional.
  An account may have Macie enabled in us-east-1 but not in eu-west-1.
  If the account has S3 buckets in multiple regions, audit each region
  independently.

- NEVER overlook `findingsFilters` with `action: ARCHIVE`. These filters
  auto-suppress findings before operators see them. A filter matching
  "all findings in bucket X" can hide an entire bucket's worth of
  sensitive data discoveries. Concrete example: an ARCHIVE filter set to
  suppress MEDIUM-severity findings in `s3://app-logs/` will also
  suppress a HIGH-severity AWS credential finding that Macie
  mis-categorised as MEDIUM due to context scoring — the SOC never sees
  the exposed key. Always enumerate active filters during the audit and
  cross-reference each filter's criteria against the full severity range.

- NEVER treat Macie findings as real-time. Even with ASDD, there is a
  latency (up to 24 hours) between when sensitive data is uploaded to S3
  and when Macie discovers it. The `createdAt` timestamp is when Macie
  detected the data, not when it was uploaded. For real-time protection,
  pair Macie with S3 Event Notifications.

- NEVER assume managed data identifiers cover every data type your
  organisation considers sensitive. Macie provides 150+ managed patterns,
  but proprietary data formats (employee IDs, custom token formats)
  require custom data identifiers. An audit that finds zero findings may
  simply lack the right detection patterns.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (archiving findings, enabling ASDD, creating or modifying classification
  jobs, updating allow-lists), the auditor MUST emit:
  `CONFIRM: About to <action> in account <account> (<region>). This
  affects <consequence>. Proceed? (yes/no)`
- Before archiving a finding, verify that the underlying sensitive data
  has been investigated and remediated. Archiving without investigation
  hides the finding from future queries without addressing the exposure.
- Before enabling ASDD, estimate the scanning cost. ASDD scans all
  monitored S3 buckets in the account. Provide a cost estimate based on
  total bucket size.
- Before removing or scoping an allow-list entry, export the current
  allow-list for rollback:
  `aws macie2 get-allow-list --id <id> --output json > /tmp/allow-list-backup-$(date +%s).json`.
- Before modifying a findings filter, verify the filter's current
  criteria and action. A filter with `action: ARCHIVE` that is modified
  to `action: NOOP` will un-suppress all previously auto-archived
  findings — potentially flooding the findings queue.

## Remediation guidance

### For NO_CLASSIFICATION

1. **Enable ASDD** for continuous sampling coverage:
   `aws macie2 update-automated-discovery-configuration --status ENABLED`.
2. **Create a classification job** for full-scan coverage on
   sensitive buckets:
   `aws macie2 create-classification-job --name <job-name> --job-type
   ONE_TIME --s3-job-definition '{"bucketDefinitions":[{"accountId":"<acct>","buckets":["<bucket>"]}]}'`.
   For compliance, use `samplingPercentage: 100`.
3. If a job exists but FAILED, check the job role IAM permissions and S3
   bucket existence, then recreate:
   `aws macie2 describe-classification-job --job-id <id>` to get failure
   details.
4. Verify coverage after 24 hours:
   `aws macie2 list-classification-jobs --results-window
   start=2026-01-01T00:00:00Z,end=2026-12-31T23:59:59Z`.

### For UNTRIAGED_FINDINGS

1. **Prioritise credential findings first.** An exposed AWS access key is
   an immediate compromise risk. Rotate the key, then investigate
   CloudTrail for unauthorised API calls during the exposure window.
2. **Verify PII findings.** Download flagged objects and confirm the
   detected data is real (not test data or false positives). If real PII,
   move to an encrypted, access-restricted bucket or delete if no longer
   needed.
3. **Archive findings only AFTER remediation:**
   `aws macie2 update-findings --finding-ids <id1> <id2> --status ARCHIVED`.
4. Set up a recurring triage cadence (daily for HIGH, weekly for MEDIUM)
   to prevent findings backlog.

### For CONFIG_GAP

**Security Hub export disabled (Step 3a):**
1. Enable publishing to Security Hub:
   `aws macie2 put-findings-publication-config --security-hub-configuration
   publishClassificationFindings=true,publishPolicyFindings=true`.
2. Export existing findings manually:
   `aws macie2 export-findings`.

**Allow-list too broad (Step 3b):**
1. Review each wildcard-prefix entry.
2. Replace `s3://bucket/*` with specific object paths:
   `s3://bucket/known-test-data/sample.json`.
3. Update the allow-list:
   `aws macie2 update-allow-list --id <id> --criteria
   '{"s3Bucket":"<bucket>","s3Prefix":"<specific/path/>"}'`.

**Auto-archive filter active (Step 3c):**
1. Review each filter's criteria and the count of findings it has
   auto-archived.
2. If the filter is masking real findings, change its action:
   `aws macie2 update-findings-filter --id <id> --action NOOP`.
3. Re-evaluate previously auto-archived findings for legitimacy.

**ASDD stale (Step 3d):**
1. Check for service-level issues or IAM permission drift on the Macie
   service-linked role.
2. If needed, disable and re-enable ASDD:
   `aws macie2 update-automated-discovery-configuration --status DISABLED`
   then `--status ENABLED`.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit (quarterly) to detect coverage drift.
3. Recommend adding custom data identifiers for organisation-specific
   sensitive data formats not covered by managed identifiers.

## Recent AWS features (2024-2026)

> The 2024-2026 feature notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load on demand when checking recent feature availability.

## Reference — Expert knowledge — non-obvious Macie behaviors

> The full expert-knowledge catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — ASDD sampling, deterministic interval sampling, USER_CANCELLED partial results, initialRun blind spot, severity vs count semantics, silent truncation, CDI regex no-op, archived-vs-remediated, Security Hub non-retroactivity, allow-list wildcards, ARCHIVE filters, per-GB cost, managed identifier limits.
> Load it when a verdict is borderline or an edge case is not covered by the steps.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — the expert-knowledge catalog of non-obvious Macie behaviors, the Step 1 FAILED-job edge case, and 2024-2026 feature notes.
- [references/error-handling.md](references/error-handling.md) — pagination guidance and AccessDeniedException / IAM-failure handling for the pre-flight gate.

## Domain

AWS CloudOps / Data Security & Compliance — Amazon Macie.

## AWS documentation

- **Amazon Macie User Guide** — https://docs.aws.amazon.com/macie/latest/user/what-macie.html
- **Macie Security** — https://docs.aws.amazon.com/macie/latest/user/security.html
- **Macie API Reference** — https://docs.aws.amazon.com/macie/latest/APIReference/macie.html
- **AWS CLI Command Reference (Macie)** — https://docs.aws.amazon.com/cli/latest/reference/macie2/
- **Macie managed data identifiers** — https://docs.aws.amazon.com/macie/latest/user/managed-data-identifiers.html
- **Macie findings** — https://docs.aws.amazon.com/macie/latest/user/findings.html
