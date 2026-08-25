---
name: cost-optimization-hub-recommendations-auditor
description: Audits AWS Cost Optimization Hub configuration for recommendation enablement, member-account coverage in Organizations, effort-level distribution, and stale high-value unactioned recommendations. Emits a deterministic verdict (DISABLED | NO_MEMBER_ACCOUNTS | HIGH_EFFORT | CONFIG_GAP | OK) per account with enumerated findings and CLI remediation. Use when checking whether Cost Optimization Hub is enabled, whether member accounts are enrolled, whether effort levels indicate missed quick wins, or whether high-savings recommendations are going stale.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config-snapshot classification. Live-account audits use aws ce get-preferences, aws ce list-cost-optimization-recommendations, aws ce list-cost-optimization-recommendation-summaries, and aws organizations list-accounts (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  verdict_shape: DISABLED | NO_MEMBER_ACCOUNTS | HIGH_EFFORT | CONFIG_GAP | OK
  when_to_use: Auditing whether Cost Optimization Hub recommendations are enabled, checking member-account enrollment in an Organizations context, evaluating effort-level distribution for missed quick wins, or identifying stale high-value recommendations that have gone unactioned beyond a savings-weighted threshold.
  activation_triggers: audit cost optimization hub, are cost optimization recommendations enabled, check member account enrollment cost optimization, effort level distribution recommendations, stale high-value recommendations, unactioned cost optimization recommendations, savings estimation mode check, FinOps audit cost optimization hub
  invocation_schema: 'Input: either (a) a Cost Optimization Hub configuration snapshot (preferences + organization context + recommendation list), OR (b) an account/profile for live-account audit. Output: deterministic VERDICT/REASON/FINDINGS/ REMEDIATION block where VERDICT is in {DISABLED, NO_MEMBER_ACCOUNTS, HIGH_EFFORT, CONFIG_GAP, OK}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Cost Optimization Hub, cost optimization, FinOps, recommendations, effort level, member accounts, savings estimation, BEFORE_DISCOUNTS, AFTER_DISCOUNTS, unactioned recommendations, right-sizing, Organizations enrollment, cost waste, resource optimization, savings plan, Compute Optimizer integration, member account coverage, stale recommendations
  tags: cost-optimization-hub, finops, cost-optimization, recommendations, organizations, audit
---

# Cost Optimization Hub Recommendations Auditor

## Mindset

**One-line takeaway:** the verdict is the **first** matching step in a priority
chain — DISABLED short-circuits everything, then member-account coverage, then
effort-level distribution, then configuration gaps. A clean OK means all four
dimensions pass.

Cost Optimization Hub (COH) aggregates cost-saving recommendations across
services (Compute Optimizer, EC2 right-sizing, EBS volume upgrades, idle-resource
termination, Lambda memory tuning). Four failure modes silently bleed money:

- **Recommendations disabled** — the tap is off; zero optimization signal flows.
- **No member accounts enrolled** — in an Organization, COH sees only the
  management account. If you have 50 member accounts, you are blind to 98% of
  your potential savings.
- **All remaining recommendations are High effort** — Low/Medium effort quick
  wins are the fast payback items. If every outstanding recommendation requires
  architectural change (High effort), the team has either exhausted quick wins
  or is skipping them — both signal a process gap.
- **High-value recommendations going stale** — a recommendation worth $500+/month
  that has sat unactioned for 90+ days is organizational inertia, not a
  technical limitation. It inflates the "potential savings" dashboard without
  delivering actual savings.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| COH not enrolled or recommendations explicitly disabled | **DISABLED** | Step 1 |
| Recommendations enabled + Org management/delegated-admin + 0 member accounts visible | **NO_MEMBER_ACCOUNTS** | Step 2 |
| Recommendations enabled + member accounts visible + ALL recommendations are High effort | **HIGH_EFFORT** | Step 3 |
| Any recommendation with estimatedSavings >= $500/mo + age > 90 days unactioned | **CONFIG_GAP** | Step 4a |
| savingsEstimationMode = BEFORE_DISCOUNTS (overstates savings) | **CONFIG_GAP** | Step 4b |
| All dimensions pass | **OK** | Step 5 |

**Priority order (first match wins):** DISABLED > NO_MEMBER_ACCOUNTS >
HIGH_EFFORT > CONFIG_GAP > OK. A configuration that is both BEFORE_DISCOUNTS
and has stale high-value recs is still CONFIG_GAP (one verdict, multiple
findings).

See the ordered steps below for edge cases. Deep COH internals (recommendation
freshness, pagination, delegation) are in the [Deep reference](#deep-reference-coh-internals)
section at the end.

## Pre-flight: organization context gate (run before classification)

Before evaluating COH configuration, classify the account context. Several
attributes **change the classification** — misjudging them produces false
positives.

**Live-account pre-flight checks (skip if doing offline snapshot audit):**
1. Verify the caller can run `ce:GetPreferences` — most read-only auditor
   roles CAN, but some SCPs block Cost Explorer APIs. Check before proceeding.
2. If the account is NOT in an Organization, Step 2 (member accounts) is
   **skipped entirely** — a standalone account has no member accounts to enroll.
   Do NOT emit NO_MEMBER_ACCOUNTS for a standalone account; that is a false
   positive.
3. If the account is an Organization **member** account (not management /
   delegated-admin), it can see its own recommendations but NOT other members.
   The member-account-coverage check (Step 2) only applies to the **management**
   or **delegated administrator** account.

| Attribute | Value | Effect on audit |
|---|---|---|
| `enrolled` | `false` | **Not enrolled.** Jump to Step 1 — DISABLED short-circuit. |
| `enrolled` | `true` | Proceed with full audit. |
| `organizationContext` | `STANDALONE` | **Standalone account.** Skip Step 2 (no member accounts to enroll). |
| `organizationContext` | `MANAGEMENT` or `DELEGATED_ADMIN` | **Org-level.** Step 2 applies — check member-account coverage. |
| `organizationContext` | `MEMBER` | **Member account.** Step 2 skipped — this account only sees its own recs. |
| `savingsEstimationMode` | `BEFORE_DISCOUNTS` | Savings estimates ignore existing RI/SP commitments — overstates actual savings. Flag in Step 4b. |
| `savingsEstimationMode` | `AFTER_DISCOUNTS` | Savings estimates account for existing commitments — accurate. No flag. |
| `memberOfServiceLevelOrganization` | `true` | Account is part of a Service Level Organization — recommendations may be visible to parent org. Informational only. |
| `memberOfServiceLevelOrganization` | `false` | Account is independent. No effect on classification. |

**If the configuration snapshot is malformed** (missing required fields, invalid
JSON), output:

```text
VERDICT: ERROR
REASON: Cost Optimization Hub configuration snapshot is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical configuration with the commands in the Quick start section and re-audit.
```

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — non-obvious COH behaviors that change classification

Full catalog (COH vs Cost Explorer, 24h generation lag, BEFORE_DISCOUNTS overstatement, enrollment vs org membership, effort-level assignment, High-effort ambiguity, age reset on refresh, 100-per-page pagination, inherited recs, RI/SP exclusions, delegated admin, monthly estimatedSavings, unstable rec IDs, Cost Categories, Terminate vs Stop, networking costs): [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 1: Recommendations enablement (highest priority)

If `enrolled` is `false` (or the preferences response is empty/default with no
recommendations ever generated):

- **DISABLED** — Cost Optimization Hub is not enrolled or recommendations are
  explicitly disabled. The account is flying blind on cost optimization with
  zero automated signal. Every dollar of waste goes undetected.

This is the highest priority because it is the foundation: without enrollment,
no recommendations exist, no savings estimates are generated, and no member
accounts can be enrolled. All downstream steps are moot.

**Edge case — enrollment < 24 hours:** If `enrolled: true` but
`enrollmentTimestamp` is less than 24 hours ago and the recommendation list is
empty, this is propagation lag, not DISABLED. Classify as OK with a note:
"Enrollment is recent (< 24h). Recommendations will appear within 24 hours."

### Step 2: Member account coverage (org-level only)

If `organizationContext` is `MANAGEMENT` or `DELEGATED_ADMIN` AND
`memberAccountsVisible` is 0 (or `memberAccountsVisible` is less than
`orgMemberAccountCount`):

- **NO_MEMBER_ACCOUNTS** — COH is enrolled but only sees the management account.
  In an Organization with N member accounts, the management account is 1/N of
  your infrastructure. Member-account recommendations are invisible, and 90%+
  of potential savings is dark.

This check only applies to management or delegated-administrator accounts. A
**standalone account** or **member account** skips this step entirely — there
are no member accounts to enroll.

**Partial enrollment:** if some but not all member accounts are visible (e.g.,
8 of 20 org member accounts show in COH), this is still a finding — emit
CONFIG_GAP (Step 4) with a note: "12 member accounts not visible in COH.
Verify org-level visibility is enabled and accounts are not suspended."

If `memberAccountsVisible` is 0 and the account IS a management account in an
org, this short-circuits to NO_MEMBER_ACCOUNTS regardless of downstream
conditions.

### Step 3: Effort level distribution

If ALL recommendations in the unactioned list have `effortLevel: High` (zero
Low or Medium effort recommendations present):

- **HIGH_EFFORT** — every outstanding recommendation requires architectural
  change or significant rework. This means either (a) all quick wins have been
  actioned and only complex items remain, or (b) COH cannot generate Low/Medium
  effort recommendations because CloudWatch utilization data is missing.

**Distinguishing exhaustion from blindness:** check whether CloudWatch agent
is deployed on EC2 instances. If CWAgent is absent, Compute Optimizer cannot
generate right-sizing recommendations (the primary source of Low-effort items),
so the "High effort only" state is a data gap, not a process win. In this case,
escalate the finding: "High-effort-only state may be caused by missing
CloudWatch agent data — verify CWAgent deployment before treating this as 'all
quick wins done'."

**Edge case — zero recommendations at all:** If enrolled > 24 hours and the
recommendation list is empty, this is NOT HIGH_EFFORT (there are no recs to
classify). Emit OK with a note: "Zero outstanding recommendations. Verify
CloudWatch agent deployment to ensure right-sizing signal is flowing."

### Step 4: Configuration gaps

If Steps 1-3 pass, check for two configuration gap conditions:

#### Step 4a: Stale high-value recommendations

If ANY recommendation has:
- `estimatedSavings >= 500` (USD/month)
- `recommendationAgeInDays > 90`
- `status: not actioned` (not implemented, not dismissed)

→ **CONFIG_GAP** — a recommendation worth $500+/month that has sat for 90+ days
is organizational inertia. The $6,000+ annual savings is being left on the
table. This is a prioritization failure, not a technical limitation.

The $500/month threshold represents ~$6,000/year — a level where the savings
justify the engineering effort to implement even a High-effort recommendation.
The 90-day threshold represents one fiscal quarter — beyond this, the
recommendation is not "in the backlog," it is abandoned.

#### Step 4b: Savings estimation mode (MANDATORY check — always evaluate)

If `savingsEstimationMode` is `BEFORE_DISCOUNTS`, the verdict is **always**
CONFIG_GAP. There is no exception. Even if the account has zero existing RI/SP
commitments today (making BEFORE_DISCOUNTS numerically identical to
AFTER_DISCOUNTS for now), the mode will diverge the moment any commitment is
purchased. AFTER_DISCOUNTS is the correct default posture.

→ **CONFIG_GAP** — BEFORE_DISCOUNTS overstates savings by ignoring existing
RI/SP commitments. Example: an m5.2xlarge at $280/month on-demand, covered by
a 3-year All-Up RI at 60% discount ($112/month actual). RIGHT-SIZE to
m5.large ($70/month on-demand):
- BEFORE_DISCOUNTS reports savings: $280 - $70 = **$210/month**
- AFTER_DISCOUNTS reports savings: $112 - $70 = **$42/month**
- BEFORE_DISCOUNTS overstates by **5x**. Teams prioritizing from
  BEFORE_DISCOUNTS numbers waste engineering effort on phantom savings.

**This step MUST be evaluated even when all recommendations are Low/Medium
effort and fresh.** A configuration that passes Steps 1-3 and Step 4a but has
`BEFORE_DISCOUNTS` is CONFIG_GAP — not OK. Do NOT skip to Step 5.

### Step 5: OK — all dimensions pass

If all four dimensions pass (enrolled, member accounts covered for org context,
mixed effort levels present or zero recommendations, no stale high-value recs,
AFTER_DISCOUNTS mode), the verdict is **OK**.

## Output format

```text
SNAPSHOT: <snapshot label>
ACCOUNT: <account-id or profile>
VERDICT: DISABLED | NO_MEMBER_ACCOUNTS | HIGH_EFFORT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [<severity>] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### ERROR output (malformed snapshot)

If the configuration snapshot is missing required fields (`enrolled`,
`organizationContext`, `preferences`), output:

```text
SNAPSHOT: <snapshot label>
ACCOUNT: <account-id>
VERDICT: ERROR
REASON: Cost Optimization Hub configuration snapshot is missing required
fields (enrolled, organizationContext, or preferences) — cannot classify.
REMEDIATION: Retrieve the configuration via:
  aws ce get-preferences --region <region> --output json
  aws organizations describe-organization --output json
  aws ce list-cost-optimization-recommendations --output json
Then re-audit with the complete snapshot.
```

### Worked example — stale high-value recommendation with BEFORE_DISCOUNTS

```text
SNAPSHOT: stale-high-value-before-discounts
ACCOUNT: 111111111111 (management account)
VERDICT: CONFIG_GAP
REASON: 2 recommendations with estimatedSavings >= $500/month have been
unactioned for >90 days (Step 4a), and savingsEstimationMode is
BEFORE_DISCOUNTS, overstating savings (Step 4b).
FINDINGS:
  - [CONFIG_GAP] Recommendation rec-001 ($850/mo, right-size i-0prodapp, High effort) unactioned for 95 days (Step 4a)
  - [CONFIG_GAP] Recommendation rec-002 ($620/mo, terminate i-0devtest, Low effort) unactioned for 112 days (Step 4a)
  - [CONFIG_GAP] savingsEstimationMode is BEFORE_DISCOUNTS — savings overstate actual incremental value (Step 4b)
  - [OK] COH enrolled, 8 member accounts visible, mixed effort levels present
REMEDIATION:
  1. Action rec-002 first (Low effort, $620/mo = $7,440/yr) — terminate the
     idle dev-test instance.
  2. Schedule rec-001 for next sprint — right-size the overprovisioned prod app.
  3. Switch savings estimation: aws ce update-preferences
     --savings-estimation-mode AFTER_DISCOUNTS.
```

## Edge-case handling

Edge-case catalog (partial enrollment, delegated admin, suspended accounts, all-sub-$500 mixed effort, BEFORE_DISCOUNTS with zero commitments, age exactly 90): [references/advanced-patterns.md](references/advanced-patterns.md).

## Anti-Patterns — NEVER

- NEVER classify a standalone account (not in an Organization) as
  NO_MEMBER_ACCOUNTS. A standalone account has no member accounts to enroll —
  the check does not apply. Flagging this is a false positive that confuses
  operators.

- NEVER treat Cost Explorer and Cost Optimization Hub as the same service.
  They share the `ce` API namespace but serve different purposes: Cost Explorer
  is a cost-analytics dashboard; COH is a recommendation engine. Pointing a
  user to Cost Explorer when they asked about "cost optimization
  recommendations" sends them to the wrong place.

- NEVER report `estimatedSavings` as an annual figure without multiplying by
  12. The field is explicitly monthly. Reporting $500/month as "$500/year"
  understates the savings by 12x and can deprioritize a valuable
  recommendation.

- NEVER assume an empty recommendation list means the account is optimized. An
  empty list can mean (a) the account is truly optimized, (b) CloudWatch agent
  is not deployed so Compute Optimizer has no data, or (c) COH enrollment is
  recent (< 24h propagation). Always verify CWAgent deployment before
  concluding "no waste."

- NEVER classify a sub-24-hour enrollment with zero recommendations as DISABLED.
  COH takes up to 24 hours to generate the first recommendation set. A fresh
  enrollment is propagation lag, not a failure.

- NEVER recommend switching savingsEstimationMode to BEFORE_DISCOUNTS as a
  remediation. BEFORE_DISCOUNTS overstates savings and leads teams to chase
  phantom savings that evaporate when existing RI/SP commitments are applied.
  AFTER_DISCOUNTS is always the correct mode for accurate prioritization.

- NEVER truncate the recommendation list by querying only the first page.
  `list-cost-optimization-recommendations` paginates at 100 per page. A
  truncated list can show only High-effort items because Low-effort items were
  on page 2+, producing a false HIGH_EFFORT verdict.

- NEVER flag the absence of Savings Plans or Reserved Instance recommendations
  as a COH gap. Commitment-based recommendations live in Cost Explorer's
  coverage APIs, not in COH. COH is a resource-level optimization engine.

- NEVER assume all High-effort recommendations are unactionable. A High-effort
  recommendation worth $2,000/month is worth prioritizing even if it requires
  a sprint of work. The HIGH_EFFORT verdict means "no quick wins remain," not
  "nothing can be done."

- NEVER ignore partial member-account enrollment. If 8 of 20 member accounts
  are visible, that is a CONFIG_GAP (not OK) — 12 accounts' waste is invisible.
  Always report the specific delta between visible and total org members.

## Pre-flight safety checks (run before any remediation CLI)

- **Read-only audit by default.** Steps 1-5 of the classification logic are
  pure read operations (`get-preferences`, `list-recommendations`). No state
  changes. The auditor can run safely in any environment.
- **Preference changes are account-level and immediate.** `aws ce
  update-preferences` takes effect immediately and applies to all users of the
  account. Before switching savingsEstimationMode, notify FinOps stakeholders
  who may reference the current numbers in reports.
- **Member-account enrollment affects the entire Organization.** Enabling
  org-level visibility makes member-account cost data visible to the management
  account. Confirm this is intended — some organizations have data-isolation
  requirements that this changes.
- **Confirmation gate for preference changes:**
  `CONFIRM: About to update Cost Optimization Hub preferences for account
  <account>. This changes savings estimation mode from <current> to <new>.
  Proceed? (yes/no)`
- **Back up current preferences before changes:**
  `aws ce get-preferences --output json > /tmp/coh-preferences-backup-$(date +%s).json`
- Prefer additive changes (enable enrollment, enable member visibility) over
  destructive changes (disable recommendations) — additive changes extend
  visibility without removing existing signal.

## Remediation guidance

### For DISABLED — COH not enrolled

1. Enroll in Cost Optimization Hub:
   ```bash
   aws ce update-preferences \
     --savings-estimation-mode AFTER_DISCOUNTS \
     --region us-east-1
   ```
2. Wait 24 hours for the first recommendation set to generate.
3. If in an Organization, enable org-level visibility (see next section).
4. Verify enrollment:
   ```bash
   aws ce get-preferences --region us-east-1
   ```

### For NO_MEMBER_ACCOUNTS — org-level visibility not enabled

1. Ensure you are calling from the management or delegated-admin account:
   ```bash
   aws organizations describe-organization --query 'Organization.MasterAccountId'
   ```
2. Enable member-account visibility. COH uses the Organizations integration —
   member accounts are enrolled automatically when the management account
   opts in. Verify the integration:
   ```bash
   aws ce get-preferences --region us-east-1
   aws organizations list-accounts --query 'Accounts[*].Id' --output json
   ```
3. Member accounts should appear within 24 hours. If they do not, verify the
   accounts are ACTIVE (not SUSPENDED) in Organizations.
4. For partial enrollment (some members missing), check for SCPs that block
   Cost Explorer APIs in the member accounts.

### For HIGH_EFFORT — no Low/Medium effort recommendations

1. Verify CloudWatch agent is deployed on EC2 instances:
   ```bash
   aws ssm describe-instance-information \
     --query 'InstanceInformationList[*].[InstanceId,PingStatus]' \
     --output table
   ```
   Without CWAgent, Compute Optimizer cannot generate right-sizing
   recommendations (the primary source of Low-effort items).
2. If CWAgent is deployed and all quick wins are genuinely actioned, document
   the remaining High-effort items as a prioritized backlog with ROI
   (estimatedSavings * 12 / engineering-estimate).
3. If CWAgent is absent, deploy it to close the data gap:
   ```bash
   aws ssm send-command \
     --document-name "AWS-ConfigureAWSPackage" \
     --parameters 'action=Install,packageName=AmazonCloudWatchAgent' \
     --targets "Key=tag:Environment,Values=production"
   ```

### For CONFIG_GAP — stale high-value recommendations

1. Sort recommendations by `estimatedSavings` descending.
2. Action Low-effort high-value items first (immediate payback).
3. Schedule High-effort high-value items for the next sprint.
4. Dismiss recommendations that are no longer relevant (resource deleted,
   architecture changed) to keep the backlog clean:
   ```bash
   # Mark a recommendation as implemented or dismissed
   aws ce update-cost-category-definition  # category management
   ```
5. Set up a monthly review cadence to prevent future staleness.

### For CONFIG_GAP — BEFORE_DISCOUNTS savings estimation

1. Switch to AFTER_DISCOUNTS:
   ```bash
   aws ce update-preferences \
     --savings-estimation-mode AFTER_DISCOUNTS \
     --region us-east-1
   ```
2. Re-prioritize the recommendation backlog using the updated (lower but
   accurate) savings estimates.
3. Communicate the mode change to FinOps stakeholders — previously reported
   savings numbers will decrease because RI/SP discounts are now netted out.

### For OK

1. No remediation required for the current posture.
2. Recommend a monthly review cadence for new recommendations.
3. If the account grows (new member accounts, new workloads), re-audit to
   catch enrollment gaps early.
4. Verify CloudWatch agent deployment on any new EC2 instances to maintain
   right-sizing signal quality.

## Deep reference: COH internals

Full internals (generation pipeline, effort-level assignment, member-account propagation, savings-estimation semantics): [references/advanced-patterns.md](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

What changed (GA expansion, resource-level filtering, Compute Optimizer aggregation): [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) - Step 0 non-obvious COH behaviors, edge-case handling, COH internals deep reference, recent AWS features

## Domain

AWS FinOps / Cost Optimization Hub Configuration & Governance.

## AWS documentation

- **AWS Cost Optimization Hub User Guide** — https://docs.aws.amazon.com/cost-optimization-hub/latest/userguide/what-is.html
- **AWS Cost Management Security** — https://docs.aws.amazon.com/cost-management/latest/userguide/security.html
- **Cost Optimization Hub API Reference** — https://docs.aws.amazon.com/cost-optimization-hub/latest/APIReference/
- **AWS CLI Command Reference — cost-optimization-hub** — https://docs.aws.amazon.com/cli/latest/reference/cost-optimization-hub/
