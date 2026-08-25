# Advanced patterns - Cost Optimization Hub Recommendations Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Step 0: Expert knowledge — non-obvious COH behaviors that change classification

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
