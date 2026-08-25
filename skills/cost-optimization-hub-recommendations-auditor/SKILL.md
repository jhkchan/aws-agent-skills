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

These behaviors are easy to misjudge without operational Cost Optimization Hub
experience. Each changes a verdict if ignored:

- **Cost Optimization Hub is NOT Cost Explorer.** Cost Explorer (`aws ce *`
  APIs for usage/cost analysis) is a reporting layer. Cost Optimization Hub is a
  recommendation engine that aggregates optimization signals from Compute
  Optimizer, Trusted Advisor, and resource-level analyzers. They share the `ce`
  API namespace but serve different purposes. A user asking about "cost
  optimization recommendations" wants COH, not a Cost Explorer chart.

- **Recommendation generation lag is 24 hours.** After enrolling or changing
  preferences, the first recommendations appear within 24 hours. An enrollment
  that is less than 24 hours old with zero recommendations is NOT a failure —
  it is propagation lag. Do NOT classify a sub-24-hour enrollment as DISABLED
  if `enrolled: true`.

- **`savingsEstimationMode: BEFORE_DISCOUNTS` systematically overstates
  savings.** This mode reports gross savings before deducting existing Reserved
  Instance (RI) and Savings Plan (SP) commitments. If you have an RI covering an
  instance at 70% discount, BEFORE_DISCOUNTS reports the full on-demand cost as
  "savings" from right-sizing — but you are already paying the RI rate, so the
  real savings is a fraction of the displayed number. AFTER_DISCOUNTS nets out
  existing commitments and gives the true incremental savings. Always recommend
  AFTER_DISCOUNTS for accurate prioritization.

- **Member-account enrollment is separate from Organization membership.** An
  account can be in your Organization and still not visible in COH. The
  management account must enable org-level visibility (which auto-enrolls all
  current member accounts). New accounts added to the org after enrollment are
  picked up within 24 hours. If member accounts were added to the org but COH
  shows zero, check whether org-level visibility was enabled — the accounts are
  there, but COH is not looking for them.

- **Effort level is assigned by AWS, not the user.** Each recommendation
  includes an `effortLevel` field: `Low`, `Medium`, or `High`. Low effort items
  (e.g., delete an idle resource, change a volume type) are quick wins with
  fast payback. High effort items (e.g., re-architect a service, migrate a
  database) require significant work. COH does not let you change the effort
  level — it is intrinsic to the recommendation type.

- **A `High effort`-only recommendation list can mean two things.** (1) All
  Low/Medium effort recommendations have been actioned (good — the team is on
  top of it). (2) No Low/Medium effort recommendations exist because CloudWatch
  metrics are missing (Compute Optimizer cannot generate right-sizing recs
  without utilization data). Distinguish between the two by checking whether
  CloudWatch agent is deployed — if not, COH is blind to right-sizing
  opportunities, and the "no quick wins" state is a false positive.

- **Recommendation age resets on refresh.** COH regenerates recommendations
  daily. The "age" of a recommendation is measured from its last refresh date,
  not its first creation. A recommendation that has been showing for 90 days
  has been refreshed 90 times — the resource is still there and still
  suboptimal. The staleness threshold (Step 4a) measures how long the
  recommendation has been continuously appearing without being actioned.

- **`list-cost-optimization-recommendations` paginates at 100 per page.**
  For accounts with hundreds of resources, a single-page query silently
  truncates. Always drain `nextToken` to completion before computing effort-level
  distribution or total savings. A truncated list can show only High-effort
  recs because Low-effort recs were on page 2+.

- **Inherited recommendations vs direct recommendations.** In an org-level COH
  view, a recommendation can be `inherited` (generated at the member-account
  level but surfaced to the management account) or `direct` (generated at the
  management-account level). Both count toward the total. When computing
  member-account coverage, check that inherited recommendations exist — their
  absence confirms member accounts are not enrolled.

- **Savings Plans and RI purchase recommendations are NOT in COH.** COH covers
  resource-level optimizations (right-size, terminate, stop, modify). Commitment-
  based recommendations (RI/SP coverage) live in Cost Explorer's
  `get-reservation-coverage` and `get-savings-coverage` APIs. Do NOT expect
  them in COH output, and do NOT flag their absence as a gap.

- **Delegated administrator for COH is separate from other delegated roles.**
  You can delegate COH administration to a member account (the delegated admin
  then sees all member recommendations). This is configured via Organizations,
  not COH preferences. If the management account delegates COH admin, the
  delegation account becomes the canonical audit target — not the management
  account.

- **`estimatedSavings` is a monthly figure, not annual.** COH reports
  `estimatedSavings` as projected monthly savings. An annual projection is
  `estimatedSavings * 12`. Do NOT multiply by 365 or report daily savings — the
  field is explicitly monthly.

- **COH recommendation IDs are NOT stable across regenerations.** Each daily
  refresh generates new recommendation IDs. A recommendation that was
  `rec-abc123` yesterday may be `rec-def456` today for the same resource and
  same action. Tracking unactioned recommendations by ID across days produces
  false "new recommendation" alerts. Track by `resourceId` + `actionType`
  instead — this pair is stable across regenerations for the same underlying
  optimization opportunity.

- **Cost Categories interact with COH savings estimation.** If you have Cost
  Categories defined (e.g., mapping costs to business units), COH savings
  estimates may not reflect category-level allocations. A recommendation that
  saves $500/month at the resource level may save $0 at a Cost Category level
  if the category's costs are dominated by shared resources. Always validate
  that resource-level savings translate to category-level savings before
  reporting savings to stakeholders.

- **`actionType: Terminate` has a permanent cost impact; `actionType: Stop`
  does not.** Terminate deletes the resource — the savings are permanent and
  the resource cannot be recovered. Stop halts the resource — savings accrue
  only while stopped, and the resource can be restarted. When prioritizing,
  Terminate recommendations have higher confidence savings (the resource is
  gone) vs Stop recommendations (the resource may be restarted, reverting
  savings). Factor this into the ROI calculation for Step 4a staleness.

- **COH does NOT consider networking costs in right-sizing recommendations.**
  An EC2 right-sizing recommendation that reduces an instance from m5.2xlarge
  to m5.large reports only the instance-hour delta. It does NOT account for
  potential changes in ENI limits, Elastic IP charges, or data transfer
  patterns that the smaller instance type may introduce. The real savings may
  be lower (or net negative) if the smaller instance requires additional
  networking resources.

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

- **Partially enrolled member accounts.** If `memberAccountsVisible` > 0 but
  < `orgMemberAccountCount`, emit CONFIG_GAP (not NO_MEMBER_ACCOUNTS — some
  members ARE visible). Note the specific missing accounts.

- **Delegated administrator account.** If the audited account is a delegated
  administrator, treat it as the management account for Step 2. The delegated
  admin sees all member recommendations — if it shows 0 member accounts, the
  delegation was set up but org-level visibility was not enabled.

- **Organization with suspended member accounts.** Suspended accounts do not
  generate cost data and should not count toward `orgMemberAccountCount` for
  coverage comparison. Subtract suspended accounts before computing coverage.

- **Recommendation list with mixed effort levels but all high-value.** If
  there are Low and Medium effort recommendations but ALL have
  estimatedSavings < $500/mo, Step 4a does not trigger (no stale high-value
  recs). The verdict depends on Step 4b (savings estimation mode).

- **BEFORE_DISCOUNTS with zero existing commitments.** If the account has zero
  RIs and zero Savings Plans, BEFORE_DISCOUNTS and AFTER_DISCOUNTS produce
  identical numbers. Still flag BEFORE_DISCOUNTS as CONFIG_GAP — the mode will
  diverge as soon as any commitment is purchased, and AFTER_DISCOUNTS is the
  correct default posture.

- **Enrollment timestamp exactly at boundary.** If `recommendationAgeInDays`
  is exactly 90, count it as >90 (the recommendation has been visible for a
  full quarter). Use `>= 90` as the stale threshold.

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

### Recommendation generation pipeline

COH aggregates recommendations from multiple sources:
1. **Compute Optimizer** — EC2 right-sizing, EBS volume type upgrades, Lambda
   memory tuning, ASG optimization. Requires CWAgent for memory metrics.
2. **Trusted Advisor cost-optimization checks** — idle resources, unassociated
   Elastic IPs, underutilized RDS instances.
3. **Resource-level analyzers** — idle NAT gateways, unattached EBS volumes,
   obsolete snapshots.

Each recommendation includes: `resourceId`, `resourceType`, `actionType`
(Terminate, Rightsize, Stop, Modify), `effortLevel` (Low, Medium, High),
`estimatedSavings` (monthly), and `recommendationAgeInDays`.

### Effort level assignment

AWS assigns effort levels based on the recommendation type:
- **Low:** Terminate idle resource, stop unused instance, change volume type
  (gp2 to gp3).
- **Medium:** Right-size EC2 instance (requires stop/modify/start cycle),
  delete old snapshots.
- **High:** Migrate database engine, re-architect service architecture,
  refactor Lambda to container.

These are intrinsic — the user cannot change them.

### Member account propagation

When the management account enables org-level visibility:
1. All ACTIVE member accounts are auto-enrolled.
2. SUSPENDED accounts are excluded.
3. New accounts added to the org after enrollment are picked up within 24
   hours of joining.
4. Delegated administrator accounts see the same view as the management
   account.

### Savings estimation semantics

| Mode | Formula | Accuracy |
|---|---|---|
| `AFTER_DISCOUNTS` | Net savings after deducting existing RI/SP commitment usage | Accurate — reflects true incremental savings |
| `BEFORE_DISCOUNTS` | Gross savings at on-demand rates | Overstates savings for resources already covered by commitments |

Example: an m5.2xlarge ($0.384/hr on-demand, ~$280/month) covered by a 3-year
All-Up RI at 60% discount. RIGHT-SIZE to m5.large ($0.096/hr):
- BEFORE_DISCOUNTS savings: $280 - $70 = $210/month
- AFTER_DISCOUNTS savings: $112 (RI rate) - $70 = $42/month

The BEFORE_DISCOUNTS number is 5x the real incremental savings.

## Recent AWS features (2024-2026)

- **GA with expanded recommendation types (2024):** Cost Optimization Hub moved to GA with new recommendation types including EBS volume right-sizing, ECS task right-sizing, and Savings Plan exchange recommendations. Auditors should verify that all applicable recommendation types are enabled in the COH preferences.
- **Resource-level filtering (2024-2025):** COH now supports resource-level and account-level filtering on recommendations. Auditors should verify that exclusions are documented and intentional — silently excluded resources can hide significant waste.
- **Integration with AWS Compute Optimizer:** COH now aggregates Compute Optimizer findings directly. Auditors should cross-reference COH recommendations with Compute Optimizer findings to ensure consistency.

## Domain

AWS FinOps / Cost Optimization Hub Configuration & Governance.

## AWS documentation

- **AWS Cost Optimization Hub User Guide** — https://docs.aws.amazon.com/cost-optimization-hub/latest/userguide/what-is.html
- **AWS Cost Management Security** — https://docs.aws.amazon.com/cost-management/latest/userguide/security.html
- **Cost Optimization Hub API Reference** — https://docs.aws.amazon.com/cost-optimization-hub/latest/APIReference/
- **AWS CLI Command Reference — cost-optimization-hub** — https://docs.aws.amazon.com/cli/latest/reference/cost-optimization-hub/
