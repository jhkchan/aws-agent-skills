---
name: inspector2-coverage-finding-auditor
description: >-
  Audits Amazon Inspector2 coverage gaps and finding severity to determine
  whether EC2 instances, ECR repositories, and Lambda functions are
  effectively scanned and free of exploitable vulnerabilities or
  misconfigurations. Classifies each resource into a single
  CRITICAL / HIGH / MEDIUM / LOW / COVERED verdict by reasoning over
  Inspector2 enablement state, per-resource coverage status (SSM-agent
  dependency for EC2, scanOnPush for ECR, Lambda code-scanning opt-in),
  network-reachability amplification of CVEs, finding lifecycle (OPEN vs
  SUPPRESSED), and resource criticality tier (production vs non-prod).
  Use when reviewing Inspector2 findings, checking scan coverage, auditing
  vulnerability posture before production deployment, validating that EC2
  instances are enrolled in Inspector2, or triaging which findings to
  remediate first. Triggers: Inspector, Inspector2, vulnerability scan,
  coverage gap, CVE, CVSS, package vulnerability, network reachability,
  ECR scanOnPush, Lambda code scan, SSM agent, scan coverage, finding
  severity, exploit, KEV, CISA, security posture.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Requires an LLM-based agent runtime (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI calls needed for classification — the skill
  reasons over provided Inspector2 state, coverage data, and finding
  records. For live-account audits, AWS CLI v2 with
  inspector2:ListCoverage, inspector2:ListFindings,
  inspector2:BatchGetAccountStatus, and ecr:DescribeRepositories
  permissions.
keywords:
  - Inspector2
  - Amazon Inspector
  - vulnerability scanning
  - coverage gap
  - CVE
  - CVSS
  - package vulnerability
  - network reachability
  - ECR scanOnPush
  - Lambda code scan
  - SSM agent
  - scan coverage
  - finding severity
  - exploit
  - KEV
  - CISA
  - security posture
  - misconfiguration
tags:
  - aws
  - inspector2
  - security
  - vulnerability-management
  - coverage-audit
  - cve
  - network-reachability
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
when_to_use: >-
  Reviewing Inspector2 findings or coverage status, auditing vulnerability
  posture before production deployment, checking whether EC2 instances are
  enrolled in Inspector2, validating ECR scanOnPush configuration, triaging
  which findings to remediate first, or performing a compliance audit of
  vulnerability-management coverage.
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

**Absence of evidence is not evidence of absence.** Inspector2's dashboard
can show "no findings" for two radically different reasons: (a) the resource
was scanned and is clean, or (b) the resource was never scanned so nothing
could be found. This skill resolves that ambiguity by verifying coverage
FIRST, then evaluating findings. A verdict is only as trustworthy as the
coverage that produced it — a CRITICAL CVE on an unscanned instance is
invisible, and the skill must surface the coverage gap itself as the risk.

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

**Contradictory data handling (explicit decision branches):**

| Data Contradiction | Classification | Reason |
|---|---|---|
| Finding references a resource with no coverage entry | **MEDIUM** | Data inconsistent — cannot verify coverage |
| Coverage says ACTIVE but SSM PingStatus is offline | **HIGH** (prod) / **MEDIUM** (standard) | SSM offline overrides coverage status |
| Finding says OPEN but `lastScannedAt` is more recent than `findingUpdatedAt` | **MEDIUM** | Finding may be stale — next scan will reconcile |
| Input provides scanOnPush for ECR but no `lastScannedAt` | **MEDIUM** | Never scanned despite scanOnPush — cannot confirm ACTIVE |
| Multiple coverage records for the same resource with different statuses | Use the WORST status | Conservative — the worse record reflects a real gap |

Check the Inspector2 account-level batch status
(`aws inspector2 batch-get-account-status`). For each resource type:

- **EC2 scanning** `status: ENABLED` → proceed to Step 1 coverage check.
- **EC2 scanning** `status: DISABLED` → ALL EC2 instances in this region are
  uncovered. If ANY EC2 instance exists in the region, this is a blanket
  coverage gap (Step 2).
- **ECR scanning** `status: ENABLED` → ECR scanning is on, but per-repo
  `scanOnPush` still matters (Step 1).
- **ECR scanning** `status: DISABLED` → ALL ECR images are uncovered.
- **LAMBDA scanning** `status: ENABLED` → Lambda standard scanning on.
  Check for code-scanning opt-in separately.
- **LAMBDA scanning** `status: DISABLED` → ALL Lambda functions uncovered.
- **LAMBDA_CODE scanning** `status: ENABLED` → deep code scanning on
  (catches dependency-graph vulnerabilities beyond runtime).

### Step 1: Per-resource coverage assessment

For each resource in the input, determine coverage using the type-specific
criteria. Coverage is NOT just "Inspector2 is enabled" — it requires that
the resource is actually enrolled and recently scanned.

**EC2 coverage (four conditions, ALL required):**

1. The instance is in `running` state. Inspector2 does NOT scan stopped
   instances — a stopped instance retains its last-known findings but is
   not re-evaluated. Treat a stopped instance as UNCOVERED (the stale
   findings do not reflect the current AMI/package state when the
   instance is next started). If the input shows `State: stopped` or
   `State: stopped` in the EC2 metadata, coverage is inactive.
2. The SSM agent is running on the instance and the instance is
   SSM-managed (`PingStatus: Online` in
   `aws ssm describe-instance-information`). Inspector2 delegates EC2
   scanning to the SSM agent — no SSM agent = no scan, period.
3. Inspector2 EC2 scanning is `ENABLED` (Step 0).
4. `lastScannedAt` is within **7 days** (Inspector2 continuously rescans
   EC2 instances; a stale timestamp means the agent stopped reporting or
   the instance was stopped and restarted). If `lastScannedAt` is `null`,
   empty, or absent, the instance has NEVER been scanned — treat as
   UNCOVERED (not ACTIVE).

If any condition fails, the EC2 instance is **UNCOVERED**.

**ECR coverage (three conditions, verified in order):**

> **MANDATORY scanOnPush verification gate:** Before classifying ANY ECR
> resource, you MUST explicitly check and state the `scanOnPush` value.
> If `scanOnPush` is not present in the input, state: "scanOnPush not
> provided — treating as false (UNCOVERED)" and classify accordingly.
> Do NOT silently assume scanOnPush=true. This is the most common ECR
> classification error.

1. Inspector2 ECR scanning is `ENABLED` (Step 0). If DISABLED, ALL ECR
   images in the region are UNCOVERED — skip remaining checks.
2. The repository has `scanOnPush: true` (images are scanned automatically
   on push) OR the specific image has a recent `scanStatus` (scanned
   within 30 days via manual trigger). If `scanOnPush: false` and no
   recent manual scan exists, the repo/image is **UNCOVERED**.
3. `lastScannedAt` is within **30 days** for ACTIVE coverage. If
   `lastScannedAt` is `null` or absent, the image has never been scanned —
   treat as UNCOVERED (not ACTIVE).

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

Note: ECR images are NOT continuously rescanned like EC2 instances — a CVE
published after the image was pushed will NOT be detected unless the image
is re-scanned or re-pushed. This is a critical coverage limitation for
production images. ECR enhanced scanning (Inspector2 continuous rescans)
re-evaluates images against the latest CVE database without requiring a
re-push — if enhanced scanning is enabled, treat the coverage as ACTIVE
regardless of lastScannedAt age (Inspector2 is continuously re-checking).

**Lambda coverage (two conditions):**

1. Inspector2 LAMBDA scanning is `ENABLED`.
2. For code-level vulnerabilities (dependency analysis), LAMBDA_CODE
   scanning must also be `ENABLED`. Standard Lambda scanning only covers
   the runtime environment, not the function code or its dependencies.

If standard scanning is on but code scanning is off, coverage is
**PARTIAL** — treat as MEDIUM coverage gap at most (the function's code
dependencies are not checked for known CVEs).

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

**Worked example:** an ECR repo last scanned 45 days ago is in the
30–90 day ECR range → STALE_MODERATE → MEDIUM for production. Do NOT
compare 45 days against the EC2 threshold of 30 days (that would
incorrectly classify it as STALE_SEVERE/HIGH). The thresholds are
per-resource-type because EC2 is continuously scanned (so 7+ days is
already stale) while ECR is push-time scanned (so 30+ days is the
expected interval for a monthly release cadence).

**Compliance tags do NOT independently escalate severity.** A `compliance=pci`
tag classifies the resource as SENSITIVE tier (which maps to the
PRODUCTION/SENSITIVE column above), but it does NOT add additional severity
levels beyond the matrix. A PCI-tagged ECR repo with a MEDIUM CVE and
STALE_MODERATE coverage is MEDIUM — not HIGH — because the matrix says
STALE_MODERATE + PRODUCTION/SENSITIVE = MEDIUM.

**Expert note on the SSM dependency:** the single most common cause of
false "COVERED" verdicts is an EC2 instance where Inspector2 EC2 scanning
is enabled but the SSM agent is not running. The Inspector2 console shows
the instance as "registered" (because it exists in the account) but no
scans run. Always check `ssm describe-instance-information --query
'InstanceInformationList[?PingStatus==`Online`]'` — if the instance is not
in that list, it is uncovered regardless of Inspector2 settings.

### Step 3: Finding assessment — filter to actionable findings

For resources with ACTIVE coverage (Step 1), assess findings. Apply these
filters BEFORE severity classification:

1. **Only OPEN findings count.** Inspector2 finding lifecycle:
   - `OPEN` — active, needs remediation. COUNTS toward verdict.
   - `SUPPRESSED` — auto-suppressed by Inspector2 (package removed from
     image/instance) or manually suppressed. Does NOT count. These are
     resolved.
   - `CLOSED` — manually resolved or auto-closed after fix verification.
     Does NOT count.
2. **INFORMATIONAL findings do not escalate.** Inspector2 emits
   INFORMATIONAL findings for reachability notes and non-vulnerability
   observations. A resource with only INFORMATIONAL findings is COVERED.
3. **De-duplicate by package+version.** The same CVE in the same package
   version across multiple finding IDs counts as ONE finding. Inspector2
   may emit multiple finding records for the same vulnerability across
   different scan paths — aggregate by `packageVulnerabilityId` or
   `cve` + `affectedPackage` + `affectedVersion`.
4. **Check `fixAvailable` for remediation triage.** Each Inspector2 finding
   includes a `fixAvailable` boolean. If `true`, a patched version of the
   vulnerable package exists and the remediation is straightforward (patch
   or upgrade). If `false`, no upstream fix exists yet — the finding
   cannot be resolved by patching alone. For `fixAvailable: false` on a
   CRITICAL or HIGH finding, note in REMEDIATION that a compensating
   control (WAF rule, network isolation, runtime patch) is required until
   the upstream project ships a fix. This does not change the verdict
   severity, but it changes the remediation guidance fundamentally.
5. **Check `inspectorScore` and `exploitabilityDetails`.** Beyond CVSS,
   Inspector2 provides an `inspectorScore` that adjusts the base CVSS
   based on AWS-specific reachability data, and `exploitabilityDetails`
   that indicates if a known exploit exists. If
   `exploitabilityDetails.lastKnownExploitInDays` is present and low
   (< 30 days), the vulnerability is being actively exploited — treat
   identically to a CISA KEV listing (escalate to CRITICAL per Step 4).

### Step 4: Finding base severity and reachability amplification

Each OPEN finding has a `severity` field from Inspector2 (CRITICAL, HIGH,
MEDIUM, LOW) based on CVSS v3 scoring. But CVSS alone does not capture
exploitability in YOUR environment. Apply the **reachability amplification
escalation** — the core expert delta:

**Network reachability cross-reference:**

Inspector2 emits `NETWORK_REACHABILITY` findings that describe what is
reachable from the internet or internal network. Cross-reference each
package/code vulnerability finding against reachability findings for the
same resource:

- If the resource has a `NETWORK_REACHABILITY` finding with
  `protocol: TCP` and `portRange` matching the vulnerable service port,
  AND `reachability: ReachableFromInternet` → the CVE is **internet
  exploitable**. Escalate severity by one level (MEDIUM→HIGH,
  HIGH→CRITICAL).
- If the reachability is `ReachableFromInternalNetwork` (reachable from
  other instances in the VPC but not the internet) → do NOT escalate,
  but note the lateral-movement risk in REMEDIATION.
- If no reachability finding exists, assume the CVE is NOT internet
  exploitable (keep base severity). The absence of a reachability finding
  means Inspector2 did not detect an open path — this is generally
  reliable for EC2 but may miss application-layer exposure.

**Reachability staleness caveat:** NETWORK_REACHABILITY findings are
point-in-time assessments snapshotting the security-group and route-table
state at scan time. If the SG was modified after the reachability finding
was generated (check CloudTrail for recent
`AuthorizeSecurityGroupIngress` / `RevokeSecurityGroupIngress` events),
the reachability data may be stale. Before escalating based on a
reachability finding, note its age: if the finding is older than the most
recent SG change, mark the reachability as UNVERIFIED in the REASON field
and keep the base severity. Do NOT blindly escalate on stale reachability
data — a false "internet-reachable" escalation triggers unnecessary
incident-response.

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

### Step 5: Finding type taxonomy and severity context

Inspector2 finding types carry different risk profiles beyond their CVSS:

- **PACKAGE_VULNERABILITY** — a CVE in an installed package (OS-level or
  application dependency). Severity is CVSS-based. These are the most
  common finding type for EC2 and ECR.
- **CODE_VULNERABILITY** — a vulnerability in Lambda function code
  (detected by Lambda code scanning). These are application-level issues
  (hardcoded secrets, insecure deserialization, SQL injection). Severity
  is assigned by Inspector2's static analysis, not CVSS.
- **NETWORK_REACHABILITY** — describes network paths, not vulnerabilities
  per se. Used as an amplification signal (Step 4), not a standalone
  severity driver.
- **MISCONFIGURATION** — Inspector2 detects security misconfigurations
  (e.g., public S3 bucket, overly permissive SG). These map to the
  security-auditor skills (s3-public-access-auditor,
  ec2-security-group-auditor) for deep classification. For this skill, a
  MISCONFIGURATION finding's severity is taken from Inspector2's
  classification.

### Step 6: Resource-level aggregation

A resource may have multiple findings AND a coverage state. The
resource-level verdict is the **worst** of:

1. The coverage gap severity (Step 2), if any.
2. The highest escalated finding severity (Step 4), if any open findings.

Where CRITICAL > HIGH > MEDIUM > LOW > COVERED.

If the resource has ACTIVE coverage (Step 1) AND zero OPEN findings above
INFORMATIONAL, the verdict is **COVERED** — the sole "safe" state.

### Step 7: Account/region-level aggregation

When auditing an entire account or region, aggregate across all resources:

1. Collect all resource-level verdicts.
2. The account/region verdict is the **worst** verdict across all
   resources.
3. In the output, list each resource with its individual verdict, then the
   aggregate.

A single CRITICAL resource makes the entire account CRITICAL. This is
intentional — one exploitable vulnerability is an active breach path.

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

1. **SSM Agent enrollment** — EC2 instances must be enrolled in Systems
   Manager. This requires the SSM agent to be installed (default on
   Amazon Linux 2/2023, Ubuntu 16.04+, needs manual install on other
   AMIs), the instance to have an IAM role with
   `AmazonSSMManagedInstanceCore`, and outbound connectivity to SSM
   endpoints (direct, via NAT gateway, or via VPC endpoints for
   air-gapped VPCs).
2. **Region enablement** — Inspector2 is regional. Enabling it in
   us-east-1 does NOT cover resources in eu-west-1. In a multi-region
   account, verify each region where resources exist. A common gap:
   Inspector2 enabled in the "primary" region but resources deployed in
   a "secondary" region for latency or DR.
3. **Organizations delegated admin** — in AWS Organizations, Inspector2 is
   configured from a delegated admin account. Member accounts inherit the
   configuration, but a member account can independently disable
   scanning (unless restricted by the admin). Always check per-account
   status, not just the delegated admin.
4. **ECR re-scan gap** — unlike EC2 (continuously scanned), ECR images are
   scanned once at push time (if `scanOnPush: true`). A CVE published
   after the push will NOT be detected until the image is re-scanned or
   re-pushed. For production images that are rarely rebuilt, this is a
   silent coverage degradation. Enable ECR enhanced scanning (Inspector2
   continuous rescans) or schedule periodic re-scans for production repos.
5. **Stopped instances** — Inspector2 does not scan stopped EC2 instances.
   A stopped instance retains its findings from the last scan but is not
   re-evaluated. If the instance is started later, Inspector2 resumes
   scanning — but the gap during the stopped period is invisible.
6. **`lastScannedAt` is scan START, not completion** — the timestamp
   records when Inspector2 began the assessment, not when it finished.
   For instances with large package inventories (>500 installed packages),
   the full assessment can take 10-30 minutes. A resource with
   `lastScannedAt: 2026-08-04T10:00:00Z` and zero findings at
   `2026-08-04T10:05:00Z` may simply not have completed the scan yet.
   If the timestamp is very recent (< 30 minutes), note in the output:
   "scan may still be in progress — zero findings is preliminary."
7. **ListFindings pagination** — `aws inspector2 list-findings` returns
   max 100 findings per page. Large accounts with thousands of findings
   MUST paginate (`--next-token`). When the input provides findings data,
   verify that it represents a complete set, not just the first page. If
   the finding count seems abnormally low for a large production fleet,
   note: "finding data may be truncated — verify pagination was applied."
8. **Fargate coverage gap** — Inspector2 does NOT independently scan
   container images running on Fargate. Coverage depends entirely on the
   ECR repo having scanning enabled. A Fargate task running an image from
   an ECR repo with `scanOnPush: false` has NO vulnerability scanning,
   even if Inspector2 EC2 and ECR are both "enabled" at the account level.
   When auditing container workloads, always trace back to the source ECR
   repo's scanning configuration.
9. **Finding eventual consistency** — after patching a vulnerability, the
   Inspector2 finding remains OPEN until the next scan cycle completes
   (typically within 24 hours for EC2, immediately for ECR on re-push).
   Do NOT classify a resource as still vulnerable based on a finding that
   predates a known patch application. If the input indicates the patch
   was applied but the finding is still OPEN, note: "finding may be stale
   — next scan cycle will confirm remediation."
10. **`inspectorScore` NULL for new CVEs** — when a CVE is newly published,
    AWS's internal analysis may not have completed yet, leaving
    `inspectorScore` as NULL while the `severity` field shows a
    preliminary rating. In this case, fall back to the raw CVSS score for
    severity classification and note: "inspectorScore pending — using NVD
    CVSS as fallback." This is common for CVEs published within the last
    48 hours.

### Expert decision tree — Inspector2-specific edge cases

These are scenarios where a capable model's general knowledge of
vulnerability scanning is insufficient. The correct classification requires
Inspector2-specific internal behavior:

**Q: An EC2 instance shows coverage `ACTIVE` but has zero findings AND zero
reachability findings. Is it COVERED?**

Not necessarily. If the SSM agent is online but the Inspector2 assessment
has never completed a full scan cycle (the `lastScannedAt` is null or
matches the enrollment timestamp), the instance is enrolled but not yet
assessed. Inspector2's initial assessment can take 10-30 minutes after
enrollment. During this window, the instance has ACTIVE status but no
meaningful finding data. Classify as **MEDIUM** (coverage pending), not
COVERED.

**Q: An ECR repo has `scanOnPush: true` but the image was pushed 6 months
ago. The scan shows zero findings. Is it COVERED?**

No. ECR basic scanning evaluates the image at push time only. CVEs
published in the last 6 months are invisible. The `lastScannedAt`
timestamp is stale (STALE_SEVERE per Step 1). Recommend ECR enhanced
scanning (Inspector2 continuous rescans) which re-evaluates images against
the latest CVE database without requiring a re-push. Classify as **HIGH**
if production, **MEDIUM** otherwise.

**Q: A Lambda function has standard scanning ENABLED and code scanning
DISABLED. It has zero findings. Is it COVERED?**

No — it has PARTIAL coverage. Standard Lambda scanning checks the runtime
environment (the managed AWS runtime, e.g., `nodejs20.x`) but NOT the
function's deployment package or layers. If the function imports a
vulnerable npm package or Python library, that CVE is invisible without
code scanning. Classify as **MEDIUM** for production functions, **LOW** for
non-production. The remediation is to enable LAMBDA_CODE scanning.

**Q: A finding has `status: OPEN` but the `packageVulnerabilityId` matches
a finding that was SUPPRESSED on a different resource. Is it still OPEN?**

Yes — suppression is per-resource, not per-CVE. If `log4j-core 2.14.1` is
SUPPRESSED on instance A (because the package was removed from A's AMI) but
still OPEN on instance B (where the package is still installed), the finding
on B remains OPEN and actionable. Do not propagate suppression status
across resources. De-duplicate by CVE+package+version for counting, but
evaluate `status` independently per resource.

**Q: A resource has both a CRITICAL CVE finding and a DENY in its security
group (no inbound traffic). Is the CVE still CRITICAL?**

Yes. The CVE severity is based on the vulnerability, not the current
network exposure. However, the reachability amplification (Step 4) would
NOT escalate because there is no `ReachableFromInternet` finding (the SG
denies inbound). The base CRITICAL severity (CVSS >= 9.0) stands — a
future SG change could expose the vulnerability. Note the SG-based
mitigation in REMEDIATION as a containment measure, but the verdict remains
CRITICAL because the vulnerable package is still installed.

**Q: An EC2 instance is in an Auto Scaling Group that regularly replaces
instances. Are the findings from the old instance still valid?**

No. Findings are tied to the specific instance ID. When an ASG replaces an
instance, the old instance's findings are auto-suppressed (the instance no
longer exists). The new instance gets fresh findings after Inspector2
completes its initial scan. However, if the AMI or launch template contains
the same vulnerable packages, the new instance will produce the same
findings — the root cause is the AMI, not the instance. Recommend patching
the AMI/launch template, not individual instances.

**Q: The `inspectorScore` differs from the NVD CVSS score for the same
CVE. Which one drives the severity?**

Inspector2's `inspectorScore` adjusts the base NVD CVSS based on
AWS-internal reachability and runtime context. For example, a CVE with
CVSS 9.0 might have `inspectorScore: 7.0` if AWS determines the vulnerable
code path is unreachable in the specific AMI/kernel combination. Use the
`inspectorScore` (not raw CVSS) when determining the finding's effective
severity — it is more accurate for YOUR specific environment. However, the
`severity` field (CRITICAL/HIGH/MEDIUM/LOW) is already derived from the
inspectorScore, so in practice you use the `severity` field directly.
Expert nuance: if `inspectorScore` is significantly lower than CVSS (>= 2
points), note in REMEDIATION that AWS's runtime analysis reduced the
effective risk — but the vulnerable package should still be patched to
eliminate the residual risk.

**Q: A multi-architecture ECR image (amd64 + arm64) has a CVE only in the
arm64 manifest. Does scanOnPush catch it?**

Yes, but only if both manifests are present. Inspector2 scans each
manifest independently. A CVE in only the arm64 variant produces a finding
scoped to that manifest digest. When auditing ECR coverage, verify that
the `imageDigest` in the finding matches the manifest actually deployed.
A common gap: teams deploy the amd64 image (clean) but the arm64 image
(used by Graviton instances) has unpatched CVEs that go unnoticed because
the audit only checked the default manifest.

**Q: A Lambda function imports a vulnerable Lambda Layer. Is the function
covered by Inspector2?**

Partially. Inspector2 Lambda code scanning evaluates the function's
deployment package, but Lambda Layers are scanned as part of the function
that imports them — not independently. If a shared Layer has a CVE, every
function consuming that Layer inherits the finding. When auditing Lambda
coverage, check for shared Layers across functions: a single vulnerable
Layer can amplify impact across dozens of functions. The remediation is
to patch the Layer and update all consuming functions to the new Layer
version.

**Q: The Inspector2 delegated admin account was removed from AWS
Organizations. What happens to member-account coverage?**

All member accounts lose their Inspector2 configuration within 24 hours
of the delegated admin removal. Existing findings remain (they are
per-account resources) but no new scans run. This is a silent coverage
collapse — there is no finding or alert for it. If the input shows
Inspector2 was recently configured via delegated admin and the admin
account status is unknown, verify each member account independently with
`aws inspector2 batch-get-account-status` per account. A recently
disrupted delegation is one of the highest-impact coverage gaps because
it affects ALL resource types across ALL member accounts simultaneously.

**Q: A finding has `fixAvailable: false` on a CRITICAL CVE. How should
this change the verdict and remediation?**

The VERDICT does not change — the CVE is still CRITICAL severity and the
vulnerable package is still installed. However, the REMEDIATION must
shift from "patch the package" to "apply compensating controls":
restrict the security group to deny inbound on the vulnerable port, add
a WAF rule to block exploit signatures, or deploy a runtime patch
(e.g., hot-patching the vulnerable function via LD_PRELOAD or a
sidecar interceptor). Note in REMEDIATION: "No upstream fix available —
compensating control required until CVE is patched upstream. Monitor
the upstream project for a fix release." This is a critical distinction:
`fixAvailable: false` means the normal patch workflow will NOT resolve
the finding, and the reviewer must know this to plan remediation
correctly.

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

*MEDIUM (stale ECR scan + MEDIUM CVE):*
```text
AUDIT ID: ecr-prod-stale-scan
RESOURCE: ECR/ecr-prod-payments
VERDICT: MEDIUM
REASON: ECR scanOnPush=true but lastScannedAt 45 days ago (STALE_MODERATE,
30-90 day ECR range) on production/PCI repo → MEDIUM per coverage matrix.
One OPEN MEDIUM CVE (CVE-2024-3456, node 18.19.0, CVSS 5.3) — no escalation
(not internet-reachable, not in KEV). Worst of (MEDIUM coverage gap,
MEDIUM finding) = MEDIUM.
COVERAGE: STALE_MODERATE
FINDINGS: 1 OPEN (0 CRITICAL, 0 HIGH, 1 MEDIUM, 0 LOW, 0 INFORMATIONAL)
REMEDIATION: Rebuild image with patched node 18.20+ and push to trigger
scanOnPush. Enable ECR enhanced scanning for continuous CVE re-evaluation.
```

*LOW (active coverage, single LOW CVE):*
```text
AUDIT ID: ec2-low-cve-only
RESOURCE: EC2/i-dev-sandbox-03
VERDICT: LOW
REASON: Active coverage (lastScannedAt < 7 days, SSM Online). One OPEN LOW
CVE (CVE-2024-9999, curl 7.81.0, CVSS 2.7) — not internet-reachable, not
in KEV. No escalation.
COVERAGE: ACTIVE
FINDINGS: 1 OPEN (0 CRITICAL, 0 HIGH, 0 MEDIUM, 1 LOW, 0 INFORMATIONAL)
REMEDIATION: Track in vulnerability backlog. Include in next patching cycle.
```

*COVERED (active ECR, zero open findings):*
```text
AUDIT ID: ecr-scanonpush-clean
RESOURCE: ECR/eci-prod-frontend
VERDICT: COVERED
REASON: scanOnPush=true, lastScannedAt < 24 hours (ACTIVE). Zero OPEN
findings at or above LOW. One SUPPRESSED finding (excluded from count).
COVERAGE: ACTIVE
FINDINGS: 0 OPEN (0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW, 0 INFORMATIONAL)
REMEDIATION: None required — actively scanned, zero open findings.
```

**Account-level aggregation (different format — use when auditing an
entire account/region, not a single resource):**

```text
ACCOUNT: 123456789012 | REGION: us-east-1
VERDICT: CRITICAL
REASON: 3 of 15 resources CRITICAL. i-prod-web-01 has OPEN CRITICAL CVE
confirmed internet-reachable. i-prod-db-01 UNCOVERED (SSM offline, prod).
ecr-prod-api scanOnPush=false with 2 OPEN HIGH CVEs.

RESOURCE SUMMARY:
  i-prod-web-01 (EC2)       — CRITICAL  [internet-reachable critical CVE]
  i-prod-db-01 (EC2)        — HIGH      [SSM offline, production uncovered]
  ecr-prod-api (ECR)        — HIGH      [scanOnPush=false + 2 open HIGH CVEs]
  lambda-report-gen (Lambda)— MEDIUM   [code scanning disabled, standard only]
  i-dev-sandbox-03 (EC2)    — COVERED   [active scan, zero open findings]

REMEDIATION: Fix i-prod-web-01 immediately (incident-response). Re-enroll
i-prod-db-01 in SSM. Enable scanOnPush on ecr-prod-api.
```

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

- Confirm the resource exists and is in the expected account/region:
  `aws inspector2 list-coverage --filter-criteria <criteria>` — fail
  closed (skip remediation) if the resource is not in the coverage list.
- Before suppressing a finding (to avoid false suppression), capture the
  full finding detail:
  `aws inspector2 batch-get-finding-details --finding-ids <id> > /tmp/<id>-backup-$(date +%s).json`.
  Suppression is reversible, but the original finding detail should be
  retained for audit trails.
- Before patching an EC2 instance (to remediate a CVE), verify the
  patch is available in the SSM Patch Baseline:
  `aws ssm describe-patch-baselines` and check the instance's patch
  compliance state. Applying a patch not in the baseline can break the
  workload.
- For ECR remediation (rebuilding an image with patched base layers),
  confirm the new base image digest BEFORE pushing. A typo in the base
  image tag can introduce a DIFFERENT vulnerability. Use
  `aws ecr describe-images` to verify the base layer.
- For internet-reachable CRITICAL findings, treat as incident response:
  contain FIRST (restrict the security group or detach the internet
  gateway), then patch. Patching takes time; containment is seconds.
  Capture forensic state (CloudTrail, VPC Flow Logs) after containment.

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

- **Lambda function code scanning (2024):** Inspector now scans Lambda function code (not just packages) for vulnerabilities. This adds `LambdaFunctionCode` as a scan type. Auditors should verify that Lambda code scanning is enabled in the Inspector2 configuration — it is a separate enablement flag from Lambda package scanning.
- **SBOM export (2024):** Inspector can now export Software Bill of Materials (SBOM) in CycloneDX format for EC2, ECR, and Lambda resources. Auditors should verify that SBOM export is configured for compliance-sensitive workloads.
- **Amazon Q vulnerability remediation (2024-2025):** Inspector integrates with Amazon Q for AI-driven vulnerability remediation suggestions. No new audit-surface fields, but auditors should note that remediation tracking now includes Q-generated fix suggestions.
- **Enhanced network reachability analysis (2024):** Inspector's network reachability analysis now includes broader coverage of security group configurations and ENI attachment states. Auditors should verify that network reachability findings are correlated with current security group state (not stale SG rules).
- **Deep inspection GA (2024-2025):** Inspector Deep Inspection scans all packages on EC2 instances (not just OS-level). Auditors should verify that Deep Inspection is enabled for production instances — it requires SSM Agent and additional configuration.

## References

- AWS Inspector2 Documentation: coverage statistics, finding types, and
  API reference for `ListCoverage`, `ListFindings`,
  `BatchGetAccountStatus`.
- CISA Known Exploited Vulnerabilities (KEV) catalog:
  `https://www.cisa.gov/known-exploited-vulnerabilities-catalog` —
  cross-reference CVE IDs against this catalog for real-world
  exploitability escalation.
- MITRE ATT&CK technique mapping: Inspector2 MISCONFIGURATION and
  NETWORK_REACHABILITY findings map to ATT&CK techniques for threat-model
  correlation.

## Section taxonomy (CloudOps auditor pattern)

This skill follows the CloudOps auditor skill pattern, with sections in
this canonical order:

1. **Frontmatter** — name, description, version, metadata.
2. **Quick reference** — three core rules.
3. **Mindset** — the two-axis (coverage + severity) reasoning framework.
4. **Philosophy** — guiding principle (verify coverage before trusting
   findings; verdict vs FINDINGS count separation).
5. **Decision flow summary** — high-level 6-step classification flow.
6. **Classification logic** — ordered decision tree (Steps 0-7) with
   inline matrices and edge-case handling.
7. **Output format** — per-resource template, field rules, FINDINGS
   counting rules, worked examples, and account-level aggregation.
8. **NEVER** — anti-patterns with explicit reasoning.
9. **Pre-flight safety checks** — destructive-operation constraints.
10. **Remediation guidance** — per-verdict action table.
11. **References** — CISA KEV, ATT&CK, Inspector2 API.

## Domain

AWS CloudOps / Vulnerability Management & Security Posture.

## AWS documentation

- **Amazon Inspector User Guide** — https://docs.aws.amazon.com/inspector/latest/user/what-is-inspector.html
- **Inspector API Reference (v2)** — https://docs.aws.amazon.com/inspector/v2/APIReference/
- **Inspector Security** — https://docs.aws.amazon.com/inspector/latest/user/security.html
- **Inspector CLI Reference (v2)** — https://docs.aws.amazon.com/cli/latest/reference/inspector2/
- **Lambda function code scanning** — https://docs.aws.amazon.com/inspector/latest/user/scanning-lambda-functions.html
- **SBOM export** — https://docs.aws.amazon.com/inspector/latest/user/sbom-export.html
