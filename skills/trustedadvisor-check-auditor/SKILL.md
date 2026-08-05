---
name: trustedadvisor-check-auditor
description: >-
  Audits AWS Trusted Advisor check results across cost optimization,
  performance, security, fault tolerance, and service-limits pillars for
  actionable findings, recommended actions, support-tier gating (Basic vs
  Business/Enterprise), check-result staleness, and excluded-resource blind
  spots. Emits a deterministic verdict (CRITICAL_CHECK | WARNING_CHECK |
  CONFIG_GAP | OK) per check with enumerated findings and specific CLI
  remediation. Use when reviewing Trusted Advisor check results, validating
  TA coverage, checking support-tier access to checks, diagnosing
  not_available statuses, or assessing overall TA posture before a
  compliance or operational review.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline check-result classification.
  Live-account audits use aws support describe-trusted-advisor-checks,
  aws support describe-trusted-advisor-check-result, and
  aws support refresh-trusted-advisor-check (AWS CLI v2, SSO or key-based
  credentials, Business or Enterprise support plan required for full
  coverage).
keywords:
  - Trusted Advisor
  - TA checks
  - cost optimization
  - fault tolerance
  - service limits
  - support tier
  - Business Support
  - Enterprise Support
  - Basic Support
  - check staleness
  - excluded resources
  - not_available
  - check refresh
  - Organizations delegated admin
  - S3 bucket permissions check
  - security groups check
  - idle EC2
  - compliance audit
  - operational review
tags: [trusted-advisor, governance, cost-optimization, security, fault-tolerance, service-limits, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Governance
  verdict_shape: "CRITICAL_CHECK | WARNING_CHECK | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing Trusted Advisor check results before a compliance or operational
    review, validating support-tier access to the full check catalog,
    diagnosing not_available or stale check statuses, auditing excluded
    resources that hide findings, or assessing overall TA posture across an
    account or organization.
  activation_triggers:
    - "audit Trusted Advisor checks"
    - "review TA findings"
    - "is TA configured correctly"
    - "check support tier coverage"
    - "stale Trusted Advisor results"
    - "excluded TA resources"
    - "not_available TA check"
    - "service limit exceeded"
    - "cost optimization findings"
    - "fault tolerance findings"
  invocation_schema: >-
    Input: either (a) a Trusted Advisor check result (JSON or text, including
    check name, category, status, timestamp, flagged resources), optionally
    paired with account metadata (support tier, total checks available,
    exclusions), OR (b) a check-id for live-account audit.
    Output: deterministic CHECK/VERDICT/REASON/FINDINGS/REMEDIATION block per
    check, where VERDICT is in {CRITICAL_CHECK, WARNING_CHECK, CONFIG_GAP, OK}.
---

# Trusted Advisor Check Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and three Trusted Advisor behaviours are easy to misjudge —
support-tier gating (Basic sees 7 of ~115 checks), per-resource status
divergence (a `warning` check can hide an `error` resource), and check
staleness (an `ok` status from 3 days ago is not trustworthy).

Trusted Advisor is AWS's native best-practices inspector across five
pillars: Cost Optimization, Performance, Security, Fault Tolerance, and
Service Limits. The audit goal is not to re-run the checks — it is to
classify the *results* the operator has provided into a deterministic
severity that drives action, while catching the structural gaps that
silently undermine trust in TA data:

- **Support tier is the fundamental constraint.** Basic and Developer
  support plans expose approximately 7 checks (Service Limits + a few core
  Security checks). The remaining ~100+ checks — covering Cost Optimization,
  Performance, Fault Tolerance, and most Security checks — require Business,
  Enterprise On-Ramp, or Enterprise support. An audit that does not flag a
  Basic-tier account is auditing < 10% of the risk surface and calling it
  "clean."
- **Per-resource status can diverge from check-level status.** A check with
  overall `warning` status may have individual flagged resources at `error`
  status. The check-level status is an aggregate; the per-resource status is
  the actual finding. Always evaluate per-resource when detailed results are
  available.
- **`not_available` is NOT `ok`.** `ok` means the check evaluated and found
  no issues. `not_available` means the check could not evaluate at all
  (missing prerequisites, unsupported configuration, service not enabled). A
  `not_available` security check may be hiding a finding — treat it as a
  CONFIG_GAP, never as "passed."

## Quick reference — severity thresholds

| Condition | Verdict | Step |
|---|---|---|
| Support tier Basic/Developer (7 of ~115 checks accessible) | **CONFIG_GAP** | Step 0 |
| Security check, status `error`, result fresh | **CRITICAL_CHECK** | Step 2 |
| Fault Tolerance check, status `error`, result fresh | **CRITICAL_CHECK** | Step 2 |
| Service Limits check, usage >= 100% of quota | **CRITICAL_CHECK** | Step 3 |
| Any check, status `not_available` | **CONFIG_GAP** | Step 2 |
| Check result timestamp > 24 hours old | **CONFIG_GAP** (additive) | Step 1 |
| Cost Optimization check, status `error` | **WARNING_CHECK** | Step 2 |
| Performance check, status `error` | **WARNING_CHECK** | Step 2 |
| Service Limits check, usage 80-99% of quota | **WARNING_CHECK** | Step 3 |
| Security/Fault Tolerance check, status `warning` | **WARNING_CHECK** | Step 2 |
| Excluded resources on Security/Fault Tolerance check | escalate one level | Step 4 |
| All checks `ok`, Business+ support, fresh results, no exclusions | **OK** | Step 5 |

See the ordered steps below for edge cases. Deep TA API internals (two
namespaces, refresh throttling, Organizations integration) are in the
[Deep reference](#deep-reference-trusted-advisor-api-internals) section.

## Pre-flight: support tier gate (run before check classification)

Before evaluating any check result, classify the account's support tier.
This **short-circuits** the audit — auditing a Basic-tier account without
flagging the coverage gap produces a false sense of security.

**Live-account pre-flight checks (skip if doing offline check-result audit):**
1. Confirm the caller can invoke
   `aws support describe-trusted-advisor-checks --language en` — if this
   returns `SubscriptionRequiredException`, the account has Basic or
   Developer support and only ~7 checks are accessible. Surface this BEFORE
   the operator asks "why are only 7 checks showing."
2. Verify CloudTrail is logging `support:Describe*` and
   `support:Refresh*` API calls — TA audit activity is not logged by default
   in CloudTrail management events unless the CloudTrail is configured for
   read-event logging on the Support service.
3. If the account is in an Organization, check whether a delegated admin is
   configured: `aws trustedadvisor describe-organization`. Without a
   delegated admin, TA runs per-account and there is no org-level
   aggregation.

| Support tier | Checks accessible | Effect on audit |
|---|---|---|
| **Basic** | ~7 (Service Limits + core Security) | **CONFIG_GAP** — 90%+ of risk surface is invisible. The 7 available checks may all be `ok` but the account is NOT clean. |
| **Developer** | ~7 (same as Basic) | Same as Basic — Developer adds only a response-time SLA, not more TA checks. |
| **Business** | All (~115) | Full audit proceeds. All five pillars covered. |
| **Enterprise On-Ramp** | All (~115) | Same as Business for TA purposes. |
| **Enterprise** | All + Premium features | Full audit + org-level aggregation, custom checks, enhanced reporting. |

**If the check result input is malformed** (missing `status`, missing
`checkName` or `checkId`, or unparseable JSON), output:

```text
CHECK: <check-name or check-id, or "unknown">
VERDICT: ERROR
REASON: Check result is malformed — missing required field (status, checkName, or checkId). Cannot classify.
REMEDIATION: Re-fetch the check result with `aws support describe-trusted-advisor-check-result --check-id <id> --language en --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Support tier evaluation

If the account support tier is **Basic** or **Developer**:

- The account has access to approximately **7 of ~115** Trusted Advisor
  checks. The remaining checks — covering Cost Optimization, Performance,
  Fault Tolerance, and most Security findings — are inaccessible.
- Even if every available check shows `ok`, the overall posture verdict is
  **CONFIG_GAP** because 90%+ of the risk surface is unevaluated.
- Do NOT classify individual Basic-tier check results as OK without the
  CONFIG_GAP caveat. An operator who reads "OK" without the coverage caveat
  will believe their account is clean when it is not.

If the support tier is **Business**, **Enterprise On-Ramp**, or
**Enterprise**: proceed to Step 1.

**Support tier detection from check count:** if the input does not
explicitly state the support tier, infer it from the total check count:
`totalChecksAvailable <= 10` → Basic/Developer. `totalChecksAvailable > 10`
→ Business or above.

### Step 1: Check result freshness

Extract the check result `timestamp` (the `lastRefreshedAt` or `timestamp`
field on the check result). Compute the age relative to the current time.

- **Timestamp > 24 hours old** → **CONFIG_GAP** (additive finding). The
  check result is stale — it does not reflect the current account state. An
  `ok` status from 3 days ago is not trustworthy; the condition may have
  degraded since.
- **Timestamp <= 24 hours old** → Fresh. No freshness finding.
- **Timestamp missing** → CONFIG_GAP (additive). Cannot determine freshness
  — treat as potentially stale.

**Freshness is additive, not overriding:** if a check has status `error`
and is stale, the `error` is still the primary finding (it was real at the
time of evaluation). Staleness adds a CONFIG_GAP finding but does not
downgrade the `error` to OK. Conversely, if a check has status `ok` and is
stale, the CONFIG_GAP (staleness) IS the verdict — the `ok` is unreliable.

### Step 2: Check status evaluation by category

Classify the check based on its **category** (pillar) and **status** field.
Apply this matrix — the first matching row is the check's severity:

| Category | Status | Severity | Rationale |
|---|---|---|---|
| **Security** | `error` | **CRITICAL_CHECK** | Active security exposure — open ports, public buckets, missing MFA. |
| **Security** | `warning` | **WARNING_CHECK** | Potential security weakness requiring review. |
| **Fault Tolerance** | `error` | **CRITICAL_CHECK** | Availability risk — no backups, single-AZ, no failover. A fault-tolerance error means the workload is one failure away from downtime. |
| **Fault Tolerance** | `warning` | **WARNING_CHECK** | Reduced resilience — degraded but not broken. |
| **Cost Optimization** | `error` | **WARNING_CHECK** | Money waste — idle resources, unattached volumes. Never CRITICAL: cost waste does not cause outages or breaches. Conflating waste with security dilutes the severity signal. |
| **Cost Optimization** | `warning` | **WARNING_CHECK** | Minor inefficiency. |
| **Performance** | `error` | **WARNING_CHECK** | Performance degradation — under-provisioned resources. Not a security or availability risk. |
| **Performance** | `warning` | **WARNING_CHECK** | Minor performance inefficiency. |
| **Service Limits** | any | **Step 3** | Graduated severity based on usage percentage — see Step 3. |
| Any category | `not_available` | **CONFIG_GAP** | Check could not evaluate. Different from `ok` — the condition is unknown, not verified clean. May be hiding a finding. |
| Any category | `ok` | **OK** | Check evaluated and passed. |

**Why Security and Fault Tolerance errors are CRITICAL but Cost and
Performance errors are WARNING:** Security errors expose the account to
breach or data loss — the impact is potentially catastrophic and immediate.
Fault tolerance errors mean the workload cannot survive a failure event —
the next AZ outage or hardware failure takes it down. Cost and Performance
errors waste money or degrade speed, but they don't cause breaches or
outages. A CRITICAL verdict that fires for an idle EC2 instance trains
operators to ignore CRITICAL.

**Per-resource divergence:** if the check result includes
`flaggedResources`, evaluate each resource's individual `status` field. A
check with overall `warning` status but one resource at `error` status
should be classified by the **worst per-resource status**, not the
check-level aggregate. The check-level status is a summary; the per-resource
status is the finding.

### Step 3: Service limits graduated severity

Service Limits checks are special — they have a graduated severity model
based on how close the usage is to the quota. Unlike other checks where
`error` is binary, service limits have three zones.

For each flagged resource in a Service Limits check, extract the metadata
fields (typically `Limit` or `Threshold` and `CurrentUsage`):

- **Usage >= 100% of limit** → **CRITICAL_CHECK**. The quota is exhausted —
  new resource creation will fail with `LimitExceededException`. If this is
  an EC2 instance limit or VPC limit, the workload cannot scale until a
  quota increase is granted (which takes hours to days).
- **Usage 80-99% of limit** → **WARNING_CHECK**. Approaching the limit —
  headroom is shrinking. Request a quota increase proactively; do not wait
  for the limit to be hit.
- **Usage < 80%** → **OK**. Sufficient headroom.

Compute the percentage yourself: `(currentUsage / limitValue) * 100`. Do
NOT trust the check-level `status` label alone — TA may report `warning`
for a limit that is actually at 100% if the data was refreshed mid-cycle.
The raw numbers in the flagged resource metadata are authoritative.

**Field-name variations across API versions:** the legacy API
(`support describe-trusted-advisor-check-result`) returns metadata as an
ordered string array — the field names come from the check's
`metadataTemplate` in `describe-trusted-advisor-checks`, not from keys in
the result. The new API (`trustedadvisor batch-get-recommendations`)
returns key-value pairs. Common field-name variants for service-limit
metadata:

- Limit value: `Limit`, `Threshold`, `Limit Code`, `Maximum`
- Current usage: `Current Usage`, `currentUsage`, `Used`, `Consumed`

If neither a limit-like nor a usage-like field is present, classify as
CONFIG_GAP per the absent-usage-metadata rule. Never guess the percentage
from the status label.

### Step 4: Excluded resources evaluation

If the check result or account metadata indicates that resources have been
excluded from this check (via `excludeCheckItems` in the legacy API or
exclusion configuration in the new API), evaluate the exclusion:

- **Excluded resources on a Security or Fault Tolerance check** → escalate
  one level. An excluded security finding is a hidden risk — the operator
  suppressed it rather than fixing it. Flag as a finding: "N resources
  excluded from this check — excluded findings are permanently hidden until
  un-excluded."
- **Excluded resources on a Cost or Performance check** → add a
  WARNING_CHECK finding. The exclusion may be hiding waste that an operator
  chose to ignore.

Exclusions persist across refreshes — they are not temporary. An excluded
resource is permanently invisible in the check results until someone
explicitly un-excludes it.

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings from all
steps, where CRITICAL_CHECK > WARNING_CHECK > CONFIG_GAP > OK:

```text
verdict = max(support_tier_finding, freshness_finding, check_status_finding,
              service_limit_finding, exclusion_finding)
```

If no findings (Business+ support, fresh result, status ok, no exclusions,
service limits < 80%), the verdict is **OK**.

## Output format (per check)

```text
CHECK: <check-name or check-id>
VERDICT: CRITICAL_CHECK | WARNING_CHECK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the check category, status, and classification step>
FINDINGS:
  - [CRITICAL_CHECK] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — security check with error status

```text
CHECK: Security Groups - Specific Ports Unrestricted (security-sg-open-error)
VERDICT: CRITICAL_CHECK
REASON: Security pillar check with status "error" — open SSH (port 22) to
0.0.0.0/0 on sg-security-sg-open-error (Step 2). Result is fresh (2 hours
old).
FINDINGS:
  - [CRITICAL_CHECK] Security check status "error": port 22 open to
    0.0.0.0/0 on sg-security-sg-open-error (Step 2)
REMEDIATION:
  1. Restrict the security group inbound rule for port 22 to the specific
     source CIDR or security group that needs SSH access.
  2. Verify with: aws ec2 describe-security-groups --group-ids
     sg-security-sg-open-error --output json.
```

### Worked example — service limits at 100%

```text
CHECK: VPC Limit (service-limit-vpc-at-100)
VERDICT: CRITICAL_CHECK
REASON: Service Limits check — usage computed at 100% of quota (5 / 5 VPCs,
Step 3). The check-level status says "error" but the severity is driven by
the percentage, not the label. New VPC creation will fail with
LimitExceededException.
FINDINGS:
  - [CRITICAL_CHECK] VPC usage at 100% of limit (5/5) — quota exhausted,
    new resource creation blocked (Step 3)
REMEDIATION:
  1. Request a quota increase: aws service-quotas request-service-quota-increase
     --service-code vpc --quota-code L-F678F1CE --desired-value 10
  2. Release unused VPCs to stay under the current limit while the increase
     is processed.
```

## Expert edge cases

These patterns represent genuine, non-obvious Trusted Advisor behaviours
that a senior CloudOps engineer would catch but a generalist would miss.

### The two API namespaces and their permission split

Trusted Advisor APIs live in **two namespaces** with **different IAM
permissions**:

1. **Legacy: AWS Support API** (`aws support describe-trusted-advisor-*`).
   Requires `support:DescribeTrustedAdvisorChecks` and related permissions.
   This is the original API surface, available since 2015. All CLI examples
   in this skill use the legacy namespace for compatibility.

2. **New: AWS Trusted Advisor service** (`aws trustedadvisor *`, introduced
   2023+). Requires `trustedadvisor:Describe*`, `trustedadvisor:List*`,
   `trustedadvisor:Update*` permissions. This namespace adds Organizations
   integration and a modernized response format.

An audit role with only `support:Describe*` permissions cannot use the new
namespace, and vice versa. When building an audit pipeline, grant BOTH
permission sets so the pipeline can use whichever API is available. Do NOT
assume `support:Describe*` is sufficient — the new namespace has features
the legacy API lacks (org-level aggregation, batch check refresh).

### `not_available` vs `ok` — the silent status

The `not_available` status means the check could not evaluate — typically
because a prerequisite is missing (e.g., the CloudTrail logging check
returns `not_available` if no trail exists in the region). This is
fundamentally different from `ok`:

- `ok`: The check ran and found no issues. The control is verified.
- `not_available`: The check could not run. The control is **unverified**.

A `not_available` security check is a blind spot — it may be hiding a
finding that the check cannot detect due to missing prerequisites. Always
classify `not_available` as CONFIG_GAP and note the prerequisite that is
missing.

### Check refresh is per-check and rate-limited

`aws support refresh-trusted-advisor-check --check-id <id>` refreshes a
single check. There is no bulk "refresh all" API. The API throttles at
approximately one refresh call per second per account. An audit pipeline
that refreshes 115 checks sequentially will take several minutes and may
hit `ThrottlingException` — implement exponential backoff.

Security checks typically complete refresh within 1-5 minutes. Cost and
Performance checks may take 15-30 minutes (they analyze CloudWatch metrics
and cost data). Do NOT assume a refreshed check returns an updated result
immediately — poll
`aws support describe-trusted-advisor-check-refresh-statuses` until the
status is `success`.

### Check exclusion persistence

Resource exclusions in Trusted Advisor are **permanent across refreshes**.
When an operator excludes a resource from a check (e.g., suppresses a
specific security group from the "open ports" check because it was flagged
as a known exception), the exclusion survives every subsequent refresh.
The check result shows `ok` or `warning` without any indication that a
resource was suppressed.

This means an excluded finding is more dangerous than a resolved finding:
a resolved finding re-appears if the condition recurs; an excluded finding
stays hidden permanently. When exclusions are present, always note: "N
resources excluded from this check. Excluded resources are invisible in
future refreshes. Review exclusions periodically to ensure they are still
justified."

### Cost optimization thresholds are hardcoded (not configurable)

Trusted Advisor cost-optimization checks use **fixed thresholds** set by
AWS — they are not user-configurable:

- **Idle EC2 Instances**: average CPU utilization < 10% for 14 consecutive
  days, plus network I/O < 5 MB/s for 14 days. Daily charge > $0.05.
- **Low Utilization EC2 Instances**: average CPU utilization < 20% for 7
  consecutive days, plus network I/O < 5 MB/s for 7 days.
- **Underutilized EBS Volumes**: < 1 IOPS for 7 consecutive days. Volume
  has been unattached for at least 7 days.
- **Unassociated Elastic IPs**: EIP not associated with a running EC2
  instance for more than 24 hours.

These thresholds are conservative — a instance at 12% CPU for 13 days will
NOT be flagged by "Idle EC2" (it does not meet the 14-day window). Do not
treat TA's absence of a cost finding as "no waste" — the instance may be
below the detection threshold but still underutilized. For finer-grained
cost analysis, use Compute Optimizer (which has adjustable lookback
windows) alongside TA.

### Organizations delegated admin is opt-in

By default, Trusted Advisor runs **per-account** even in an AWS
Organization. There is no automatic org-level aggregation. To see TA
results across all member accounts from a single payer, a delegated admin
must be explicitly configured:

```bash
aws trustedadvisor enable-organization --profile management-account
```

This sets up the management account (or a delegated member) as the TA
aggregation point. Without this, an auditor checking the payer account
sees only the payer's checks — member account findings are invisible. For
a multi-account audit, always verify the delegated admin configuration
before treating the payer's TA results as org-wide.

### `describe-trusted-advisor-check-summaries` vs `-result`

The legacy API has two granularity levels:

- **`describe-trusted-advisor-check-summaries`**: returns the check-level
  status only (ok / warning / error / not_available). Fast, lightweight,
  suitable for a first-pass sweep of all 115+ checks. Does NOT include
  flagged resource details.
- **`describe-trusted-advisor-check-result`**: returns the full flagged
  resource list with per-resource status and metadata. Heavier response,
  suitable for drill-down on non-ok checks.

An efficient audit pipeline runs summaries first (identify which checks are
non-ok), then result only on the non-ok checks. This minimizes API calls
and response size. Do NOT call `result` on every check — the responses for
checks with hundreds of flagged resources are large and slow.

**Batch processing pattern for multi-check audits:**

1. Call `describe-trusted-advisor-check-summaries` once per check (or
   `batch-describe-trusted-advisor-check-summaries` in the new namespace)
   to get the status of all checks in a single pass.
2. Filter to checks where status is not `ok` (typically 5-20 out of 115+).
3. For each non-ok check, call `describe-trusted-advisor-check-result` to
   get flagged resource details.
4. Classify each result using Steps 0-5, then aggregate worst-finding-wins.

This two-phase pattern reduces API calls from ~115 to ~20 and avoids
fetching large resource lists for clean checks.

### Security check overlap with Security Hub

Several Trusted Advisor security checks overlap with AWS Security Hub
controls. The most common overlaps:

- TA "IAM Use" ≈ Security Hub [IAM.7] (password policy), [IAM.8] (MFA on
  root).
- TA "Security Groups - Specific Ports Unrestricted" ≈ Security Hub
  [EC2.14]-[EC2.18].
- TA "S3 Bucket Permissions" ≈ Security Hub [S3.1]-[S3.3].

If both TA and Security Hub are enabled, they produce duplicate findings.
When remediating, fix the issue once (it clears both). When auditing,
note the overlap to avoid double-counting severity.

### Legacy API metadata is positional, not key-value

The legacy `describe-trusted-advisor-check-result` API returns each
flagged resource's `metadata` as an **ordered string array**, not a
key-value map. The field names are defined separately in the check's
`metadataTemplate` (returned by `describe-trusted-advisor-checks`). For
example, a Service Limits check result might show `"metadata": ["5",
"5", "Amazon VPC"]` where position 0 is current usage, position 1 is the
limit, and position 2 is the service name. An audit pipeline that
assumes key-value pairs will silently misparse the data. Always map
positions to names using the `metadataTemplate` before interpreting
values.

### TA delegated admin is separate from other delegated admins

Configuring a delegated admin for Trusted Advisor
(`aws trustedadvisor enable-organization`) does NOT configure delegated
admins for Security Hub, GuardDuty, or Amazon Macie — each service
requires its own delegation. An audit that verifies org-level TA
coverage must not assume that a Security Hub delegated admin covers TA.
Check each service independently with its own API.

### Refresh status `none` is ambiguous

The refresh status `none` has two valid meanings: (a) the check has
never been refreshed, or (b) the check was refreshed successfully and
the status was cleared. Do not treat `none` as an error. Fetch the
check result directly with
`describe-trusted-advisor-check-result` — the `timestamp` on the result
tells you when it was last evaluated, which is the authoritative
freshness signal.

## Anti-Patterns — NEVER

- NEVER classify a Security check with `error` status as WARNING_CHECK or
  OK. An `error` on a security check means an active exposure (open port,
  public bucket, missing MFA). Cost waste can wait; security exposure
  cannot. The category determines the ceiling — Security errors are always
  CRITICAL_CHECK.

- NEVER classify a Cost Optimization check with `error` status as
  CRITICAL_CHECK. Cost waste — idle instances, unattached volumes, unused
  EIPs — is a financial issue, not a security or availability risk.
  Conflating waste with breach risk trains operators to ignore CRITICAL
  verdicts. Cost errors are WARNING_CHECK, always.

- NEVER treat `not_available` as equivalent to `ok`. `not_available` means
  the check could not evaluate — the control is unverified, not passed. A
  `not_available` security check may be hiding a finding (e.g., the
  CloudTrail logging check cannot run if no trail exists). Classify as
  CONFIG_GAP and note the missing prerequisite.

- NEVER audit a Basic or Developer support account and report OK without a
  CONFIG_GAP caveat. Basic/Developer exposes ~7 of ~115 checks — 90%+ of
  the risk surface (Cost Optimization, Performance, Fault Tolerance, most
  Security) is invisible. An audit that ignores the support tier is
  auditing a fraction of the surface and calling it complete.

- NEVER trust a check result timestamp older than 24 hours without flagging
  staleness. TA checks are cached snapshots — a `status: ok` from 3 days
  ago reflects the account state as of 3 days ago, not now. The condition
  may have degraded since the last refresh.

- NEVER assume the check-level `status` is the whole picture. A check with
  `warning` status may have individual flagged resources at `error` status.
  Always evaluate per-resource when the detailed result is available. The
  check-level status is an aggregate that can mask worse per-resource
  findings.

- NEVER compute service-limits severity from the check-level `status`
  alone. TA may report `warning` for a limit at 100% if the data was
  refreshed mid-cycle. Extract `limitValue` and `currentUsage` from the
  flagged resource metadata and compute the percentage yourself. The raw
  numbers are authoritative; the status label is a cache.

- NEVER classify a Service Limits check severity when usage metadata is
  absent. If the flagged resource metadata lacks both a limit/threshold
  field and a current-usage field, you cannot compute the percentage.
  Output CONFIG_GAP with the finding "usage metadata absent — cannot
  determine utilization." Guessing the severity from the check-level
  status alone violates the Step 3 rule and may over- or under-state the
  risk.

- NEVER assume that excluded resources are benign. Resource exclusions in
  TA persist across refreshes — an excluded finding is permanently hidden
  until un-excluded. An operator may have excluded a legitimate finding to
  silence noise, then forgotten about it. Always flag exclusions as a
  finding and recommend periodic exclusion reviews.

- NEVER refresh all checks sequentially without backoff. The
  `refresh-trusted-advisor-check` API throttles at approximately 1 call per
  second per account. A pipeline that refreshes 115 checks without backoff
  will hit `ThrottlingException` and silently skip checks.

- NEVER recommend upgrading from Basic to Business/Enterprise support as
  the sole remediation for limited TA coverage. While a support upgrade
  unlocks all checks, it is a significant cost commitment. The immediate
  remediation is to supplement with AWS Config rules, Security Hub, and
  Compute Optimizer (which are available at all support tiers and cover
  much of the same ground).

- NEVER treat a single TA check result as the account-wide posture verdict.
  TA checks are per-pillar, per-resource — an `ok` on the "S3 Bucket
  Permissions" check does NOT mean the account is secure. It means S3
  bucket policies are clean. Aggregate across all checks for a posture
  verdict.

- NEVER assume the `aws trustedadvisor` (new namespace) commands are
  available on older AWS CLI versions. The new namespace requires AWS CLI
  v2.11+ (released 2023+). If the CLI version is older, fall back to
  `aws support describe-trusted-advisor-*` commands. An audit pipeline
  that assumes the new namespace will fail on legacy CLI installations.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (refresh-trusted-advisor-check, exclude-check-items, un-exclude
  resources), the auditor MUST emit:
  `CONFIRM: About to <action> on check <check-id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. TA check
  refresh is rate-limited and exclusions are persistent — both can disrupt
  operational dashboards.
- Confirm the check exists and is accessible:
  `aws support describe-trusted-advisor-checks --language en --output json`
  — fail closed (skip remediation) if it returns `SubscriptionRequiredException`
  (Basic/Developer support) or the check ID is not in the response.
- Before refreshing a check, verify no other refresh is in progress:
  `aws support describe-trusted-advisor-check-refresh-statuses --check-id <id>`.
  A refresh already in `pending` or `enqueued` state will not benefit from a
  duplicate call — it will consume rate-limit quota without accelerating the
  refresh.
- Before modifying exclusions, capture the current exclusion list for
  rollback. Exclusions are not versioned — there is no undo without a
  backup of the prior state.
- Prefer additive changes (refresh a check to get fresh data, add new
  exclusions) over destructive changes (remove existing exclusions) —
  additive changes are reversible.
- For CRITICAL_CHECK findings (security error, service limit at 100%),
  treat as time-sensitive — remediate before the next operational window.
  A service limit breach blocks new resource creation; a security error is
  an active exposure.

## Remediation guidance

### For CRITICAL_CHECK — Security check with error status (Step 2)

1. Identify the specific flagged resource from the check result's
   `flaggedResources` array. The `resourceId` and `metadata` fields
   identify the exact resource and the condition that triggered the check.
2. Apply the resource-specific fix (e.g., for an open security group:
   restrict the inbound rule; for a public S3 bucket: apply
   BlockPublicAccess; for missing root MFA: enable a hardware MFA device).
3. Refresh the check to verify the fix:
   `aws support refresh-trusted-advisor-check --check-id <id>`
4. Poll the refresh status until `success`, then re-fetch the result to
   confirm the status changed to `ok`.

### For CRITICAL_CHECK — Fault Tolerance check with error status (Step 2)

1. Identify the flagged resource and the fault-tolerance gap (e.g., no
   Multi-AZ deployment, no backup configured, no health check).
2. Apply the availability fix (enable Multi-AZ, configure automated
   backups, add an ELB health check).
3. Verify via the service-specific CLI (e.g., `aws rds describe-db-instances`
   for Multi-AZ status).

### For CRITICAL_CHECK — Service Limits at >= 100% (Step 3)

1. Request a quota increase:
   `aws service-quotas request-service-quota-increase --service-code <code> --quota-code <code> --desired-value <new-limit>`
2. Quota increases are processed by AWS support and may take hours to days.
   In the interim, identify resources that can be released to stay under
   the current limit.
3. If the limit cannot be increased (e.g., hard limit), architect around
   it (e.g., use multiple accounts, switch to a service with a higher
   limit).

### For WARNING_CHECK — Cost Optimization check with error status (Step 2)

1. Identify the wasted resource (idle EC2, unattached EBS, unused EIP).
2. Snapshot/backup if needed, then stop or terminate:
   `aws ec2 stop-instances --instance-ids <id>` (idle EC2),
   `aws ec2 delete-volume --volume-id <id>` (unattached EBS after snapshot),
   `aws ec2 release-address --allocation-id <id>` (unused EIP).
3. Monitor the next billing cycle to confirm the cost reduction.

### For CONFIG_GAP — Basic/Developer support tier (Step 0)

1. If a support upgrade is justified, enable Business or Enterprise On-Ramp
   support via the AWS Support Center.
2. If a support upgrade is not feasible, supplement TA with free-tier
   alternatives:
   - **Security Hub** (free for 30 days, then per-check pricing) covers
     many of the same security controls.
   - **AWS Config managed rules** (free tier available) provides continuous
     compliance evaluation.
   - **Compute Optimizer** (free) covers EC2/EBS/Lambda rightsizing.
   - **Cost Explorer** (free) covers cost-anomaly detection and commitment
     analysis.
3. Do NOT report the account as "clean" based on 7 checks alone. Note the
   coverage gap explicitly in the audit report.

### For CONFIG_GAP — Stale check result (Step 1)

1. Refresh the check:
   `aws support refresh-trusted-advisor-check --check-id <id>`
2. Wait for refresh completion (poll
   `describe-trusted-advisor-check-refresh-statuses` until `success`).
3. Re-fetch the result and re-audit with fresh data.

### For CONFIG_GAP — not_available status (Step 2)

1. Identify the missing prerequisite (the check's description typically
   explains what it requires).
2. Enable the prerequisite (e.g., create a CloudTrail trail, enable Config
   recording, create IAM password policy).
3. Refresh the check after the prerequisite is in place.

### For OK

1. No remediation required for the current posture.
2. Recommend setting up a periodic TA review cadence (weekly or biweekly)
   to catch new findings before they escalate.
3. If the account is in an Organization, recommend configuring delegated
   admin for org-level aggregation.

## Deep reference: Trusted Advisor API internals

### Two API namespaces

| Namespace | IAM permission prefix | Introduced | Key advantage |
|---|---|---|---|
| `aws support describe-trusted-advisor-*` | `support:Describe*` | 2015 | Universally available, well-documented |
| `aws trustedadvisor *` | `trustedadvisor:*` | 2023+ | Organizations integration, batch operations, modernized response format |

An audit pipeline should attempt the new namespace first (richer features)
and fall back to the legacy namespace if the IAM permissions are not
available. Both namespaces return the same check data — the check IDs and
categories are identical across namespaces.

### Refresh lifecycle

When `refresh-trusted-advisor-check` is called, the check enters a refresh
queue. The lifecycle is:

1. `none` → check has never been refreshed or is not queued.
2. `enqueued` → refresh request accepted, waiting for evaluation.
3. `processing` → AWS is evaluating the check against current account
   state.
4. `success` → refresh complete, new results available.
5. `abandoned` → refresh failed (typically due to transient service issue).

Security checks typically complete in 1-5 minutes. Cost and Performance
checks may take 15-30 minutes (they analyze CloudWatch and cost data).
Service Limits checks are typically fast (< 1 minute). Always poll until
`success` before re-fetching results — fetching during `processing` returns
the stale result from the prior refresh.

### Organizations integration

The `aws trustedadvisor` namespace adds org-level APIs:

- `describe-organization` — check if org-level TA is enabled.
- `enable-organization` — set up the management account as the TA admin.
- `list-accounts-for-organization` — see which member accounts are
  reporting TA data to the aggregation point.
- `set-organization-access` — grant or revoke member account TA access to
  the admin.

Without organization-level TA, each member account must be audited
individually. The management account's TA results do NOT include member
account findings by default. For a multi-account audit, verify org-level
setup before relying on the management account's TA data.

### Check category reference

| Pillar | Example checks | Severity on `error` |
|---|---|---|
| **Security** | IAM Use (root MFA, access keys), S3 Bucket Permissions, Security Groups, CloudTrail Logging, IAM Access Key Age | CRITICAL_CHECK |
| **Fault Tolerance** | ELB AZ Awareness, RDS Multi-AZ, Auto Scaling Group Health, EBS Snapshot, Route 53 Health Checks | CRITICAL_CHECK |
| **Cost Optimization** | Idle EC2 Instances, Low Utilization EC2, Underutilized EBS Volumes, Unassociated EIPs, S3 Bucket Lifecycle | WARNING_CHECK |
| **Performance** | High Performance Assurance, EC2 Instance Optimization, EBS I/O Performance | WARNING_CHECK |
| **Service Limits** | EC2 Instance Limit, VPC Limit, EBS Volume Count, Auto Scaling Groups, IAM Roles | Step 3 (graduated) |

## Domain

AWS CloudOps / Trusted Advisor Governance & Operational Excellence.
