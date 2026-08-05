# End-to-end usage scenario: cleanrooms-collaboration-auditor

A walkthrough showing the skill auditing a Clean Rooms collaboration
that has both an INVITED member (MEMBERSHIP_GAP) and missing
differential privacy (PRIVACY_RISK), demonstrating precedence
aggregation, the multi-party membership-gate concept, and the
privacy-budget remediation workflow.

## Input (user prompt)

> Review this Clean Rooms collaboration before we open it up to
> production query traffic. Two brands plus an analytics provider are
> supposed to be collaborating.

```yaml
Collaboration id: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/prod-marketing-pool
Collaboration metadata:
  name: prod-marketing-pool
  status: ACTIVE
  creatorDisplayName: 111-creator-brand-a
  creatorMemberAbilities: [CAN_QUERY, CAN_CONFIGURE_COLLABORATION]
  queryLogStatus: ENABLED
  analyticsEngine: CLEAN_ROOMS_SQL
  configuredAudienceModelArn: arn:aws:cleanroomsml:us-east-1:111111111111:configured-audience-model/cam-789

Members (list-members):
- accountId: "111111111111"
  status: ACTIVE
  displayName: 111-creator-brand-a
  abilities: [CAN_QUERY, CAN_CONFIGURE_COLLABORATION]
- accountId: "222222222222"
  status: ACTIVE
  displayName: 222-brand-b
  abilities: [CAN_QUERY]
- accountId: "333333333333"
  status: INVITED
  displayName: 333-analytics-provider
  abilities: [CAN_QUERY]

Differential privacy config:
  enabled: false

Configured table cr-events:
  allowedColumns: [user_id, event_type, ts, region]
  analysisRuleType: AGGREGATION
  aggregateConstraints: []

Per-member epsilon spend:
- accountId: "111111111111"
  epsilonSpent: 0
- accountId: "222222222222"
  epsilonSpent: 0

Configured audience model state (cleanroomsml get-configured-audience-model):
  status: READY
  trainingContainerExecutionStatus: SUCCEEDED
```

## Skill output

```text
COLLABORATION: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/prod-marketing-pool
VERDICT: MEMBERSHIP_GAP
REASON: Member 333333333333 (333-analytics-provider) is in INVITED state
(Rule M1) — the collaboration is operationally partial: the analytics
provider cannot run queries or contribute their configured table.
Differential privacy is also disabled (Rule P1) and aggregate constraints
are absent on cr-events (Rule P3), compounding the exposure once 333
activates.
FINDINGS:
  - [MEMBERSHIP_GAP] Member 333333333333 in INVITED state (Rule M1) —
    has not called CreateMembership to accept; cannot query or contribute
    data
  - [PRIVACY_RISK] differentialPrivacyConfig.enabled is false (Rule P1)
    — protected queries run against raw rows with no DP noise
  - [PRIVACY_RISK] cr-events has no aggregateConstraints (Rule P3) —
    singleton-row re-identification possible; no structural privacy floor
  - [OK] Configured audience model cam-789 is READY (Rule C1 passes)
  - [OK] All declared analysis templates have resolved parameters and
    valid table references
REMEDIATION:
  1. MEMBERSHIP_GAP — Have 333333333333 accept the invitation before
     opening production traffic:
       aws cleanrooms create-membership \
         --collaboration-arn arn:aws:cleanrooms:us-east-1:111111111111:collaboration/prod-marketing-pool \
         --membership-display-name "333-analytics-provider" \
         --profile 333-profile
     If the analytics provider is no longer intended, revoke instead:
       aws cleanrooms delete-membership \
         --membership-identifier <membership-arn-for-333>
  2. PRIVACY_RISK — Enable differential privacy BEFORE 333 activates,
     so the first query they run is privacy-protected:
       aws cleanrooms update-collaboration \
         --collaboration-identifier prod-marketing-pool \
         --differential-privacy-config enabled=true
     Set epsilonBudgetPerMember at creation for the collaboration
     lifetime — epsilon does NOT reset.
  3. PRIVACY_RISK — Add aggregate constraint MIN=10 on user_id so
     singleton-row returns are blocked regardless of DP status:
       aws cleanrooms update-configured-table-analysis-rule \
         --configured-table-id cr-events \
         --analysis-rule-type AGGREGATION \
         --analysis-rule-aggregate-columns ...
  4. Re-audit after the membership activation and privacy-control
     enablement to verify the verdict transitions to OK.
```

## What the skill caught that a generic assistant misses

1. **The membership activation gate.** A generic assistant says "one
   member hasn't accepted." The skill explains that the INVITED member
   cannot create analysis templates, run protected queries, or
   contribute their configured table — the collaboration is
   operationally partial, not just "incomplete." The verdict
   (MEMBERSHIP_GAP) reflects that no production traffic should run
   until the member activates.

2. **Precedence aggregation.** The collaboration has BOTH a membership
   gap AND privacy risks. The skill's verdict is MEMBERSHIP_GAP (the
   higher-precedence dimension), but the FINDINGS list retains the
   PRIVACY_RISK findings so the operator can remediate both in
   parallel — enabling DP BEFORE the INVITED member activates ensures
   the first query they run is privacy-protected.

3. **The "enabled ≠ enforced" DP distinction.** A generic assistant
   reads `differentialPrivacyConfig.enabled: false` as "DP is off." The
   skill notes that even after enabling DP at the collaboration level,
   each protected query's `additionalAnalyses` epsilon value is the
   actual enforcement — the capability gate and the per-query
   enforcement are separate layers.

4. **Aggregate constraints as the structural floor.** A generic
   assistant might focus only on DP. The skill flags the missing
   `aggregateConstraints` as a separate PRIVACY_RISK — without a
   MIN/MAX floor, queries can return singleton rows even with DP noise,
   because noise can round a 1-row group up to the threshold. Both
   layers must be present for defense in depth.

5. **Per-member epsilon reasoning.** The skill notes that epsilon is
   per-member, not per-collaboration — when the INVITED member
   activates, they will need their own budget allocation. The
   remediation recommends setting `epsilonBudgetPerMember` for the
   collaboration lifetime at creation, since it cannot be increased
   later without recreating the collaboration.

## Slash-command invocation

```
/aws:audit-cleanrooms-collaboration
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this Clean Rooms collaboration before production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: cleanrooms-collaboration-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the membership gap and enabling privacy controls,
validate the collaboration posture:

```bash
# Verify all members are ACTIVE
aws cleanrooms list-members \
  --collaboration-id prod-marketing-pool \
  --profile default --output table

# Confirm differential privacy is enabled
aws cleanrooms get-collaboration \
  --collaboration-id prod-marketing-pool \
  --profile default --query 'collaboration.differentialPrivacyConfig'

# Check the most recent protected query's epsilon contribution
aws cleanrooms list-protected-queries \
  --membership-identifier <membership-arn> \
  --profile default --max-results 5 --output table

# Verify the configured audience model is READY
aws cleanroomsml get-configured-audience-model \
  --configured-audience-model-arn arn:aws:cleanroomsml:us-east-1:111111111111:configured-audience-model/cam-789 \
  --profile default --query 'status'
```

Then monitor CloudTrail for `cleanrooms:StartProtectedQuery` events
from unexpected members for 1-2 weeks after opening production traffic.
