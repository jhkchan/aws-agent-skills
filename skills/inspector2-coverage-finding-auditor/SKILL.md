---
name: inspector2-coverage-finding-auditor
description: 'Audits Amazon Inspector2 coverage gaps and finding severity to determine whether EC2 instances, ECR repositories, and Lambda functions are effectively scanned and free of exploitable vulnerabilities or misconfigurations. Classifies each resource into a single CRITICAL / HIGH / MEDIUM / LOW / COVERED verdict by reasoning over Inspector2 enablement state, per-resource coverage status (SSM-agent dependency for EC2, scanOnPush for ECR, Lambda code-scanning opt-in), network-reachability amplification of CVEs, finding lifecycle (OPEN vs SUPPRESSED), and resource criticality tier (production vs non-prod). Use when reviewing Inspector2 findings, checking scan coverage, auditing vulnerability posture before production deployment, validating that EC2 instances are enrolled in. Triggers: Inspector, Inspector2, vulnerability scan, coverage gap, CVE, CVSS, package vulnerability, network reachability, ECR scanOnPush, Lambda code scan, SSM agent, scan coverage, finding severity, exploit, KEV, CISA, security posture.'
license: Apache-2.0
compatibility: Requires an LLM-based agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI calls needed for classification — the skill reasons over provided Inspector2 state, coverage data, and finding records. For live-account audits, AWS CLI v2 with inspector2:ListCoverage, inspector2:ListFindings, inspector2:BatchGetAccountStatus, and ecr:DescribeRepositories permissions.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Inspector2, Amazon Inspector, vulnerability scanning, coverage gap, CVE, CVSS, package vulnerability, network reachability, ECR scanOnPush, Lambda code scan, SSM agent, scan coverage, finding severity, exploit, KEV, CISA, security posture, misconfiguration
  tags: aws, inspector2, security, vulnerability-management, coverage-audit, cve, network-reachability
  dependencies: aws-orchestrator
  when_to_use: Reviewing Inspector2 findings or coverage status, auditing vulnerability posture before production deployment, checking whether EC2 instances are enrolled in Inspector2, validating ECR scanOnPush configuration, triaging which findings to remediate first, or performing a compliance audit of vulnerability-management coverage.
---

# Inspector2 Coverage + Finding Auditor

## Quick reference

**Three core rules** (full decision tree in Steps 0-7 below):

1. Inspector2 disabled in-region + production resources exist → **CRITICAL**.
2. EC2 without SSM agent (`PingStatus != Online`) → **UNCOVERED** (severity
   by resource tier).
3. Active coverage + zero OPEN findings at or above LOW → **COVERED**.

All other cases require the full classification logic below.

## Mindset — two axes, one verdict

Inspector2 has two independent axes: **coverage** (is this resource
actually being scanned?) and **finding severity** (what was found?). A
resource with Inspector2 "enabled" but no SSM agent is NOT covered —
the dashboard shows green because nothing was found, but nothing was
found because nothing was scanned. The verdict conflates both axes:
`COVERED` requires BOTH active coverage AND zero open actionable
findings. Classify coverage first, then finding severity, then take
the worst.

## Philosophy — verify coverage before trusting findings

→ Philosophy extended rationale moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

The second philosophical principle: **the VERDICT and the FINDINGS count
serve different purposes.** The VERDICT is the final aggregated risk rating
(coverage gap OR finding severity, worst wins, with escalation). The FINDINGS
field is a raw inventory using Inspector2's original `severity` field. These
two CAN differ — a MEDIUM finding escalated to HIGH via reachability still
appears as "1 MEDIUM" in the FINDINGS count while the VERDICT is HIGH. This
separation is non-negotiable: the FINDINGS field must never be adjusted to
match the VERDICT.

## Decision flow summary

The full classification follows this high-level flow (each step detailed
below):

1. **Validate account state** (Step 0) — Is Inspector2 enabled for this
   resource type in this region? If disabled and resources exist → CRITICAL/HIGH.
2. **Assess per-resource coverage** (Step 1) — Is THIS specific resource
   enrolled and recently scanned? EC2 needs SSM agent + 7-day freshness;
   ECR needs scanOnPush + 30-day freshness; Lambda needs code scanning.
3. **Score coverage gap** (Step 2) — If uncovered or stale, what severity
   based on resource tier (prod vs standard)?
4. **Filter findings** (Step 3) — Drop SUPPRESSED/CLOSED, de-duplicate by
   CVE+package+version, check fixAvailable and KEV status.
5. **Escalate by reachability** (Step 4) — Cross-reference NETWORK_REACHABILITY
   findings; internet-reachable escalates +1 level; KEV escalates to CRITICAL.
6. **Aggregate** (Steps 5-7) — Worst of coverage gap and finding severity =
   resource verdict; worst resource = account verdict.

Detailed thresholds, matrices, and edge cases follow in each step.

## Process — Classification logic (apply in order)

### Step 0: Validate Inspector2 account-level state and input completeness

If the input does not contain enough information to determine Inspector2
state (no coverage data, no finding records, no resource inventory), output:

```text
RESOURCE: <name-or-id>
VERDICT: MEDIUM
REASON: Insufficient Inspector2 data to classify — cannot confirm coverage or findings. This is an UNVERIFIED verdict, not a safe state.
REMEDIATION: Run aws inspector2 batch-get-account-status and aws inspector2 list-coverage to gather coverage state, then re-audit.
```

**NEVER output VERDICT: COVERED on missing data.** COVERED means "verified
safe" — both coverage confirmed AND zero open findings. Missing data means
you cannot make either assertion. Output MEDIUM with an explicit
"UNVERIFIED" note so the reviewer knows the resource has not been
audited, not that it has been cleared.

→ Contradictory-data + account-status branches moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 1: Per-resource coverage assessment

→ Step-1 coverage-definition intro moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**EC2 coverage (four conditions, ALL required):**

→ EC2 coverage conditions (detail) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

If any condition fails, the EC2 instance is **UNCOVERED**.

**ECR coverage (three conditions, verified in order):**

> **MANDATORY scanOnPush verification gate:** Before classifying ANY ECR
> resource, you MUST explicitly check and state the `scanOnPush` value.
> If `scanOnPush` is not present in the input, state: "scanOnPush not
> provided — treating as false (UNCOVERED)" and classify accordingly.
> Do NOT silently assume scanOnPush=true. This is the most common ECR
> classification error.

→ ECR coverage conditions (detail) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**ECR coverage decision tree (apply exactly):**

```
Is Inspector2 ECR scanning ENABLED?
  NO  → UNCOVERED (all ECR images in region)
  YES → Is scanOnPush true?
    NO  → Is there a recent manual scan (lastScannedAt < 30 days)?
      NO  → UNCOVERED
      YES → Assess staleness: < 30 days = ACTIVE, 30-90 = STALE_MODERATE, > 90 = STALE_SEVERE
    YES → Is lastScannedAt provided?
      NO/null → UNCOVERED (never scanned despite scanOnPush)
      YES → Assess staleness: < 30 days = ACTIVE, 30-90 = STALE_MODERATE, > 90 = STALE_SEVERE
```

→ ECR rescan limitation note moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**Lambda coverage (two conditions):**

→ Lambda coverage conditions (detail) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**Coverage state classification:**

| Coverage State | Condition | Verdict Impact |
|---|---|---|
| ACTIVE | All type-specific conditions met, `lastScannedAt` < 7 days (EC2) or < 30 days (ECR) | Proceed to finding assessment |
| STALE_MODERATE | Conditions met but `lastScannedAt` 7-30 days (EC2) or 30-90 days (ECR) | MEDIUM coverage gap |
| STALE_SEVERE | Conditions met but `lastScannedAt` > 30 days (EC2) or > 90 days (ECR) | HIGH coverage gap (effectively uncovered) |
| UNCOVERED | SSM agent offline, Inspector2 disabled, or scanOnPush false | Coverage gap — severity by resource tier |
| PARTIAL | Lambda standard scanning only (no code scanning) | MEDIUM coverage gap |

### Step 2: Coverage gap severity by resource tier

A coverage gap's severity depends on WHAT is uncovered — a production
database with no scanning is critical; a dev sandbox is medium.

**Resource tier classification:**

- **PRODUCTION** — tagged `env=prod`, `environment=production`,
  `critical=true`, OR in a production VPC (CIDR matches known prod range),
  OR the resource is a database/data-store instance type (R5, X2ed, I4,
  Im4gen, DB instances).
- **SENSITIVE** — tagged `compliance=pci`, `compliance=hipaa`,
  `data-classification=confidential`, OR processes PII/financial data.
- **STANDARD** — any resource not meeting the above.

**Coverage gap severity matrix:**

Thresholds are type-specific — EC2 and ECR have DIFFERENT staleness
windows. Do NOT apply EC2 thresholds to ECR resources or vice versa.

| Coverage State | EC2 threshold | ECR threshold | PROD/SENSITIVE | STANDARD |
|---|---|---|---|---|
| Inspector2 disabled (region-wide) | n/a | n/a | **CRITICAL** | HIGH |
| UNCOVERED (SSM offline / scanOnPush false) | n/a | n/a | **HIGH** | MEDIUM |
| STALE_SEVERE | > 30 days | > 90 days | **HIGH** | MEDIUM |
| STALE_MODERATE | 7–30 days | 30–90 days | MEDIUM | LOW |
| PARTIAL (Lambda standard only) | n/a | n/a | MEDIUM | LOW |

→ Step-2 worked example (ECR stale scan) moved verbatim to [references/worked-examples.md](references/worked-examples.md).

→ Compliance-tag + SSM expert notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 3: Finding assessment — filter to actionable findings

For resources with ACTIVE coverage (Step 1), assess findings. Apply these
filters BEFORE severity classification:

→ Step-3 filter rules (detail) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 4: Finding base severity and reachability amplification

→ Step-4 escalation prose + staleness caveat moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**CISA KEV catalog escalation:**

If the finding's CVE is listed in the CISA Known Exploited Vulnerabilities
(KEV) catalog (check the `vulnerability.id` or `cve` field against the KEV
list), escalate severity to **CRITICAL** regardless of CVSS. KEV-listed
CVEs have confirmed active exploitation in the wild — the CVSS score
understates real-world risk because a working exploit exists.

**Severity escalation matrix (final per-finding severity):**

| Inspector2 Base Severity | Internet Reachable (same port) | In KEV Catalog | Final Severity |
|---|---|---|---|
| CRITICAL | — (any) | — | **CRITICAL** |
| HIGH | Yes | — | **CRITICAL** |
| HIGH | No | Yes | **CRITICAL** |
| HIGH | No | No | HIGH |
| MEDIUM | Yes | — | HIGH |
| MEDIUM | No | No | MEDIUM |
| LOW | Yes | — | MEDIUM |
| LOW | No | No | LOW |
| INFORMATIONAL | — | — | (ignore — does not escalate) |

→ Steps 5-7 taxonomy + aggregation detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

### Pre-output validation checklist (run before emitting VERDICT)

Before emitting the final VERDICT, verify these invariants. A mismatch
indicates a reasoning error — re-check the steps above:

1. **Verdict >= highest OPEN finding severity.** If the resource has an
   OPEN CRITICAL finding, the verdict CANNOT be below CRITICAL. If it has
   an OPEN HIGH finding, the verdict CANNOT be below HIGH (unless
   reachability amplification escalated it to CRITICAL, in which case the
   verdict is CRITICAL).
2. **Verdict >= coverage gap severity.** If the resource has a HIGH
   coverage gap (Step 2), the verdict CANNOT be below HIGH — even if zero
   findings exist. No findings on an uncovered resource means "unscanned,"
   not "safe."
3. **COVERED requires both axes clear.** COVERED requires ACTIVE coverage
   (Step 1) AND zero OPEN findings at or above LOW. A single OPEN LOW
   finding → verdict is LOW, not COVERED.
   - **ECR-specific COVERED check:** before emitting COVERED for an ECR
     resource, verify: (a) `scanOnPush: true` is explicitly stated, (b)
     `lastScannedAt` is within 30 days, AND (c) enhanced scanning is on
     OR the last push was recent. An ECR repo with `scanOnPush: true` but
     a 60-day-old `lastScannedAt` is STALE_MODERATE, not COVERED.
4. **FINDINGS count matches the input.** Count only `status: OPEN`
   findings. The FINDINGS field must enumerate the exact count per
   severity level as provided in the input. Do not invent or omit
   findings. If the input says "(none)", the FINDINGS count is 0.
5. **Severity labels match Inspector2's field.** Use the `severity` value
   from the finding record exactly (CRITICAL, HIGH, MEDIUM, LOW,
   INFORMATIONAL). Do not relabel a MEDIUM finding as HIGH or vice versa
   in the FINDINGS field — the escalation happens in the VERDICT, not in
   the finding count.
6. **Reachability escalation is reflected.** If a finding was escalated by
   reachability (Step 4), the VERDICT reflects the escalated severity, but
   the FINDINGS field still shows the ORIGINAL Inspector2 severity. Note
   the escalation in the REASON field (e.g., "MEDIUM CVE escalated to HIGH
   via internet reachability").

### Effective coverage context (expert note)

Inspector2 coverage state is influenced by layers outside Inspector2's
direct control:

→ Effective-coverage expert notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

### Expert decision tree — Inspector2-specific edge cases

→ Edge-case Q&A catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Output format (per resource) — ALL fields mandatory

Echo the Audit ID from the input (if provided) in every output block. Every
field below is REQUIRED — omitting any field is an error. Generate each
field by following its inline rule:

```text
AUDIT ID: <echo-from-input>
RESOURCE: <type/name-or-id>
VERDICT: CRITICAL | HIGH | MEDIUM | LOW | COVERED
REASON: <1-2 sentences citing the specific finding or coverage gap and the rule that fired>
COVERAGE: ACTIVE | STALE_MODERATE | STALE_SEVERE | UNCOVERED | PARTIAL
FINDINGS: <count> OPEN (<N> CRITICAL, <N> HIGH, <N> MEDIUM, <N> LOW, <N> INFORMATIONAL)
REMEDIATION: <specific action, or "None required — actively scanned, zero open findings" if COVERED>
```

**Field-by-field generation rules (follow exactly):**

- **AUDIT ID:** Copy verbatim from the input. If absent, write "N/A".
- **RESOURCE:** Use the resource type and name/ID from the input (e.g.,
  "EC2/i-prod-web-01", "ECR/ecr-prod-payments").
- **VERDICT:** The worst of (coverage gap severity from Step 2, escalated
  finding severity from Step 4). CRITICAL > HIGH > MEDIUM > LOW > COVERED.
  This CAN be higher than any individual finding's Inspector2 severity due
  to reachability/KEV escalation.
- **REASON:** Cite the SPECIFIC rule that fired (e.g., "STALE_MODERATE
  coverage (45 days, ECR threshold 30-90) on prod → MEDIUM per matrix").
  If escalated, note the escalation (e.g., "HIGH CVE escalated to CRITICAL
  via internet reachability on port 443").
- **COVERAGE:** ALWAYS output this field — never omit it even for
  resources with no coverage data (output "UNCOVERED"). Determine from
  Step 1. For ECR resources, you MUST have verified scanOnPush status
  before emitting this field.
- **FINDINGS:** Count ONLY `status: OPEN` findings. Use the Inspector2
  `severity` field value for each count bucket — do NOT relabel a finding's
  severity based on escalation. The escalation affects VERDICT only.
  Format: `<total> OPEN (<n>C, <n>H, <n>M, <n>L, <n>I)`. If zero open
  findings: `0 OPEN (0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW, 0 INFORMATIONAL)`.
  Self-check: the sum of all buckets MUST equal the total count.
- **REMEDIATION:** Specific to the verdict. For COVERED: "None required —
  actively scanned, zero open findings."

**FINDINGS counting rules (critical — the FINDINGS severity buckets use
the raw Inspector2 `severity` field, NOT the escalated verdict):**

- Count ONLY `status: OPEN` findings. SUPPRESSED/CLOSED are excluded.
- De-duplicate by CVE + affectedPackage + affectedVersion before counting.
- INFORMATIONAL findings are counted but do not escalate the verdict.
- Self-check: sum of all severity buckets MUST equal the total OPEN count.

**Worked examples (one per verdict level):**

*CRITICAL (internet-reachable CVE):*
```text
AUDIT ID: ec2-critical-cve-internet-reachable
RESOURCE: EC2/i-prod-web-01
VERDICT: CRITICAL
REASON: OPEN CRITICAL CVE (CVE-2021-44228, log4j-core 2.14.1, CVSS 10.0)
confirmed internet-reachable via NETWORK_REACHABILITY finding on port 443.
Listed in CISA KEV catalog.
COVERAGE: ACTIVE
FINDINGS: 2 OPEN (1 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW, 1 INFORMATIONAL)
REMEDIATION: Incident-response priority. Contain FIRST — restrict SG to deny
inbound on port 443. Then patch log4j to 2.17.1+ via SSM Run Command.
```

→ Secondary worked examples + account-level format moved verbatim to [references/worked-examples.md](references/worked-examples.md).

## Anti-Patterns — NEVER

- NEVER classify a resource as COVERED if you have not confirmed ACTIVE
  coverage. A missing coverage record is NOT the same as "scanned with no
  findings" — it means the resource is not enrolled, and the absence of
  findings is meaningless. COVERED requires positive confirmation of both
  coverage AND zero open findings.

- NEVER treat an EC2 instance as covered just because Inspector2 EC2
  scanning is "enabled." The SSM agent must be running and reporting.
  An instance with `PingStatus: ConnectionLost` or no SSM enrollment has
  zero Inspector2 coverage regardless of the toggle. This is the #1 cause
  of false-safe verdicts.

- NEVER ignore `lastScannedAt`. A scan timestamp older than 7 days (EC2)
  or 30 days (ECR) means the coverage is stale — new CVEs published since
  the last scan are undetected. Stale coverage is a degraded state, not
  full coverage. A stale scan on a production resource is HIGH risk.

- NEVER assume ECR `scanOnPush: true` means continuous coverage. ECR
  scans images once at push time. A CVE disclosed after the push is
  invisible until the image is rebuilt or re-scanned. For long-lived
  production images, this is a silent gap. Recommend enhanced scanning
  or scheduled re-scans for production repos.

- NEVER classify a CRITICAL CVE on an internet-reachable resource as
  anything other than CRITICAL. The combination of a CVSS >= 9.0
  vulnerability + confirmed network reachability from the internet =
  confirmed exploitable attack path. This is an incident, not a backlog
  item. If the reachability finding shows `ReachableFromInternet` on the
  vulnerable port, escalate without exception.

- NEVER count SUPPRESSED or CLOSED findings toward severity. A
  SUPPRESSED finding means Inspector2 confirmed the vulnerable package
  was removed from the running image/instance — the vulnerability is
  resolved at the source. Counting it inflates severity and causes
  alert fatigue. Only `status: OPEN` findings drive the verdict.

- NEVER escalate based on INFORMATIONAL findings alone. Inspector2 emits
  INFORMATIONAL findings for reachability observations and configuration
  notes. These do not represent vulnerabilities. A resource with only
  INFORMATIONAL findings is COVERED — the findings are context, not
  defects.

- NEVER treat Lambda standard scanning as full coverage. Standard
  scanning covers the runtime environment but NOT the function code or
  its dependencies. Without LAMBDA_CODE scanning enabled, dependency
  CVEs in the function's deployment package are invisible. A Lambda with
  standard scanning only has PARTIAL coverage — classify as MEDIUM at
  best for production functions.

- NEVER assume Inspector2 is enabled in all AWS regions. Inspector2 is a
  regional service — enabling it in us-east-1 does NOT cover resources in
  eu-west-1, ap-southeast-1, or any other region. A multi-region account
  with resources in DR/latency secondary regions but Inspector2 enabled
  only in the primary region has a blanket coverage gap in every
  unconfigured region. Always verify per-region status with
  `aws inspector2 batch-get-account-status --region <each-region>` for
  every region where resources exist.

- NEVER conflate a LOW-severity OPEN finding with zero findings. A resource
  with one OPEN LOW CVE is verdict LOW, not COVERED. COVERED requires zero
  OPEN findings at or above LOW severity. INFORMATIONAL-only is COVERED;
  LOW-or-above is not. The distinction matters for compliance audits where
  "zero open findings" is the pass criterion — a LOW finding fails that bar.

- NEVER recommend disabling Inspector2 as a cost-saving measure without
  quantifying the risk. Inspector2 pricing is per-instance per-day
  (EC2) and per-image per-scan (ECR). The cost of a single undetected
  CVE on a production instance (breach, data loss, compliance fine)
  vastly exceeds the scanning cost. If cost is a concern, tune which
  resources are scanned (e.g., exclude dev sandboxes) rather than
  disabling the service.

- NEVER rely on CVSS alone for severity without checking the CISA KEV
  catalog. A CVSS 7.5 CVE with active exploitation in the wild (KEV
  listed) is more dangerous than a CVSS 9.0 CVE with no known exploit.
  The KEV catalog is the authoritative signal for real-world
  exploitability — always cross-reference.

- NEVER de-duplicate findings by finding ID alone. Inspector2 may emit
  multiple finding records for the same CVE across different scan paths
  or resource tags. De-duplicate by `cve` + `affectedPackage` +
  `affectedVersion` to avoid inflating finding counts and causing
  unnecessary alarm.

- NEVER treat a NETWORK_REACHABILITY finding as current without verifying
  the security group state. Reachability findings are point-in-time
  assessments — a subsequent SG change (adding a DENY rule, removing an
  inbound rule, or attaching a new SG) may have invalidated the finding.
  If the input shows a reachability finding but the SG configuration shows
  no matching open inbound rule on the vulnerable port, note the
  discrepancy: the reachability data may be stale. Check for recent
  `AuthorizeSecurityGroupIngress` or `RevokeSecurityGroupIngress` events
  in CloudTrail. A false "internet-reachable" escalation leads to
  unnecessary incident-response activation. When in doubt, state:
  "Reachability finding present but SG state cannot be confirmed —
  treating reachability as UNVERIFIED, base severity stands."

- NEVER assume reachability findings cover application-layer exposure.
  Inspector2's NETWORK_REACHABILITY assesses TCP/UDP path reachability
  (layers 3-4). It does NOT detect application-layer exposure (HTTP API
  endpoints, GraphQL resolvers, SSRF vectors). A port may be reachable
  but the vulnerable service may not be exposed at the application layer,
  or vice versa — an application-layer proxy may expose a service on a
  different port than the vulnerable process listens on.

## Pre-flight safety checks (run before any remediation CLI)

**Destructive operation constraints (MANDATORY):** This skill is a
CLASSIFICATION and AUDIT skill — it outputs verdicts and recommendations.
It does NOT execute remediation. If any downstream consumer uses the
skill's output to trigger automated remediation, the following constraints
are non-negotiable:

- **NEVER auto-suppress findings** (`aws inspector2 update-findings --status
  SUPPRESSED`) without human review. Suppression hides the finding from
  dashboards and can mask unresolved vulnerabilities during compliance
  audits. Suppression is reversible but creates an audit-trail gap if the
  original finding detail is not retained.
- **NEVER auto-delete or replace ECR images** as a remediation step.
  Deleting an image breaks running containers that depend on it. Always
  push a patched image and update the deployment tag instead.
- **NEVER auto-terminate or stop EC2 instances** to contain a CVE. Use
  security-group restriction (seconds, non-destructive) as the containment
  mechanism. Termination is irreversible and should require explicit human
  approval.
- **NEVER auto-disable Inspector2 scanning** on any resource type. Even
  if a resource is being decommissioned, keep scanning enabled until the
  resource is fully decommissioned to maintain the audit trail.
- **Any automated remediation triggered by this skill's output MUST
  require a human-approval gate** for CRITICAL and HIGH verdicts. The
  skill identifies risk; a human authorizes the response action.
- **Automated pipeline guardrails:** when this skill is integrated into
  a CI/CD or EventBridge-driven pipeline, the pipeline MUST implement a
  break-glass mechanism: any CRITICAL verdict blocks deployment, any
  HIGH verdict requires explicit override with a documented
  justification, and MEDIUM verdicts are logged but non-blocking. The
  skill's output is advisory — the pipeline policy enforces the gate.
  Do NOT wire verdicts directly to destructive actions without a policy
  layer in between.

→ Pre-flight safety CLI checks moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

## Remediation guidance (by verdict)

| Verdict | Action | Timeline |
|---|---|---|
| CRITICAL (internet-reachable CVE) | Contain FIRST (restrict SG on vulnerable port), then patch via SSM (`AWS-RunPatchBaseline`) / rebuild ECR image / update Lambda package. Verify finding transitions to CLOSED within 24h. | Immediate (incident response) |
| CRITICAL (coverage gap on prod) | Re-enroll in SSM (verify `AmazonSSMManagedInstanceCore` role + outbound connectivity) or enable `scanOnPush` (`aws ecr put-image-scanning-configuration`). | Immediate |
| HIGH | Fix coverage config (SSM/scanOnPush) or patch CVE via SSM Patch Manager / image rebuild. Re-scan to verify. | Current sprint |
| MEDIUM | If stale scan, trigger re-scan first. Check if CVEs entered KEV since last review. | 1-2 sprints |
| LOW | Track in backlog; include in routine patching cycles. | Monthly/quarterly |
| COVERED | No action. Verify coverage monitoring (CloudWatch/EventBridge on Inspector2 coverage changes). Recommend ECR enhanced scanning for long-lived images. | N/A |

## Recent AWS features (2024-2026)

→ Recent features + external references + section taxonomy moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (MEDIUM / LOW / COVERED) and the account-level aggregation output format.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-level status check branches; pre-flight safety CLI checks.
- [references/advanced-patterns.md](references/advanced-patterns.md) — philosophy detail; per-resource coverage condition detail; Step 3 filter rules; Step 4 escalation prose; Steps 5-7 aggregation detail; effective-coverage expert notes; edge-case Q&A; recent AWS features; external references.

## Domain

AWS CloudOps / Vulnerability Management & Security Posture.

## AWS documentation

- **Amazon Inspector User Guide** — https://docs.aws.amazon.com/inspector/latest/user/what-is-inspector.html
- **Inspector API Reference (v2)** — https://docs.aws.amazon.com/inspector/v2/APIReference/
- **Inspector Security** — https://docs.aws.amazon.com/inspector/latest/user/security.html
- **Inspector CLI Reference (v2)** — https://docs.aws.amazon.com/cli/latest/reference/inspector2/
- **Lambda function code scanning** — https://docs.aws.amazon.com/inspector/latest/user/scanning-lambda-functions.html
- **SBOM export** — https://docs.aws.amazon.com/inspector/latest/user/sbom-export.html
