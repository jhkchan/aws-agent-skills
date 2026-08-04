# End-to-end usage scenario: cost-optimization-hub-recommendations-auditor

A walkthrough showing the skill auditing a Cost Optimization Hub configuration
that has both stale high-value unactioned recommendations (CONFIG_GAP via
Step 4a) and BEFORE_DISCOUNTS savings estimation mode (CONFIG_GAP via Step 4b),
demonstrating multi-finding aggregation, the savings-overstatement concept, and
the prioritized remediation workflow.

## Input (user prompt)

> Audit our Cost Optimization Hub configuration before the quarterly FinOps
> review. We are the management account in an Organization with 12 member
> accounts.

```yaml
Account: 111111111111 (management account, Organization with 12 member accounts)

Cost Optimization Hub configuration snapshot:
  enrolled: true
  enrollmentTimestamp: "2024-06-01T00:00:00Z"
  preferences:
    savingsEstimationMode: BEFORE_DISCOUNTS
    memberOfServiceLevelOrganization: false
  organizationContext: MANAGEMENT
  orgMemberAccountCount: 12
  memberAccountsVisible: 10
  recommendations:
    - resourceId: "i-0prodapp01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Low"
      estimatedSavings: 850.00
      recommendationAgeInDays: 95
      status: "not actioned"
    - resourceId: "i-0devtest01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Terminate"
      effortLevel: "Low"
      estimatedSavings: 620.00
      recommendationAgeInDays: 112
      status: "not actioned"
    - resourceId: "i-0staging01"
      resourceType: "AWS::EC2::Instance"
      actionType: "Rightsize"
      effortLevel: "Medium"
      estimatedSavings: 180.00
      recommendationAgeInDays: 20
      status: "not actioned"
  totalEstimatedMonthlySavings: 1650.00
```

## Skill output

```text
ACCOUNT: 111111111111 (management account)
VERDICT: CONFIG_GAP
REASON: 2 recommendations with estimatedSavings >= $500/month have been
unactioned for >90 days (Step 4a), and savingsEstimationMode is
BEFORE_DISCOUNTS, overstating savings by ignoring existing RI/SP commitments
(Step 4b). Additionally, 2 member accounts are not visible in COH.
FINDINGS:
  - [CONFIG_GAP] Recommendation for i-0prodapp01 ($850/mo, Low effort right-size)
    unactioned for 95 days (Step 4a) — $10,200/yr left on the table
  - [CONFIG_GAP] Recommendation for i-0devtest01 ($620/mo, Low effort terminate)
    unactioned for 112 days (Step 4a) — $7,440/yr left on the table
  - [CONFIG_GAP] savingsEstimationMode is BEFORE_DISCOUNTS — savings overstate
    actual incremental value for resources covered by existing RI/SP commitments
    (Step 4b)
  - [CONFIG_GAP] 2 of 12 member accounts not visible in COH — verify org-level
    visibility and check for suspended accounts
  - [OK] COH enrolled since 2024-06-01, 10 member accounts visible, mixed effort
    levels present (Low, Medium)
REMEDIATION:
  1. CONFIG_GAP — Action i-0devtest01 immediately (Low effort, terminate the
     idle dev-test instance). $620/mo = $7,440/yr recovered.
  2. CONFIG_GAP – Action i-0prodapp01 in the next sprint (Low effort right-size).
     $850/mo = $10,200/yr recovered.
  3. CONFIG_GAP — Switch savings estimation:
     aws ce update-preferences --savings-estimation-mode AFTER_DISCOUNTS
  4. CONFIG_GAP — Verify the 2 missing member accounts are ACTIVE in
     Organizations and not blocked by SCPs:
     aws organizations list-accounts --query 'Accounts[?Status==`ACTIVE`]'
```

## What the skill caught that a generic assistant misses

1. **The savings overstatement trap.** A generic assistant says "you have
   $1,650/month in potential savings." The skill explains that
   BEFORE_DISCOUNTS overstates savings by ignoring existing RI/SP commitments.
   The real incremental savings could be a fraction of $1,650 — teams
   prioritizing from inflated numbers waste engineering effort on phantom
   value.

2. **The staleness threshold as an organizational signal.** A generic assistant
   says "these recommendations have been around for a while." The skill
   quantifies: $1,470/month combined, sitting for 95-112 days. That is $17,640+
   in annualized savings abandoned — not a technical limitation, but a
   prioritization failure.

3. **The partial member-account enrollment.** A generic assistant might not
   notice that 10 of 12 member accounts are visible. The skill catches the
   delta (2 accounts missing) and flags it as a coverage gap — those accounts'
   waste is invisible.

4. **Low-effort-first remediation ordering.** A generic assistant lists
   recommendations by savings amount. The skill reorders by effort level first
   (action the Low-effort $620/mo terminate before the Low-effort $850/mo
   right-size, because terminate is faster to implement).

## Slash-command invocation

```
/aws:audit-cost-optimization-hub
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit cost optimization hub before the quarterly FinOps review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: cost-optimization-hub-recommendations-auditor]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit cost optimization hub"
# [Phase: Audit | Skills routed: cost-optimization-hub-recommendations-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the configuration, validate the COH posture:

```bash
# Verify preferences were updated
aws ce get-preferences --profile default --region us-east-1

# Check recommendation list after actioning stale items
aws ce list-cost-optimization-recommendations \
  --filter '{"implemented": false}' \
  --profile default --region us-east-1

# Verify member account count
aws organizations list-accounts \
  --query 'length(Accounts[?Status==`ACTIVE`])' \
  --profile default --region us-east-1
```

Then monitor for new recommendations weekly to maintain a clean posture.
