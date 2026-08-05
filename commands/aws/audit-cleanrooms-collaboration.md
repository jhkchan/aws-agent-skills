---
description: Audit an AWS Clean Rooms collaboration for membership-status gaps (INVITED/REMOVED members), privacy-budget risks (differential privacy disabled, epsilon spend exhausted, aggregate constraints missing), analysis-template SQL-validation defects (unresolved parameters, dangling table references), and configured-audience activation gaps (audience model untrained or stale).
nl_triggers:
  - "audit this clean rooms collaboration"
  - "check clean rooms member status"
  - "is differential privacy enabled"
  - "epsilon budget exhausted"
  - "validate analysis template SQL"
  - "is my audience model trained"
  - "clean rooms membership gap"
  - "configured audience ready"
  - "privacy budget audit"
  - "protected query failed"
  - "clean rooms collaboration posture"
  - "INVITED member clean rooms"
  - "REMOVED member clean rooms"
  - "cleanrooms epsilon spend"
  - "cleanroomsml audience activation"
  - "hardening clean rooms collaboration"
routes_to: cleanrooms-collaboration-auditor
---

# /aws:audit-cleanrooms-collaboration

Activate the `cleanrooms-collaboration-auditor` skill and audit one or
more AWS Clean Rooms collaborations for membership, privacy-budget,
analysis-template, and configured-audience posture.

## What it does

Reads a Clean Rooms collaboration snapshot (collaboration metadata +
member list + differential-privacy config + per-member epsilon spend +
analysis-template bodies + configured-audience-model state) and
applies the ordered classification logic:

1. Pre-flight collaboration metadata gate — short-circuit INACTIVE
   collaborations, missing CAN_QUERY members, and Spark-engine
   special cases.
2. Membership activation — any INVITED/REMOVED/LEFT member, or fewer
   than 2 members, or no CAN_QUERY member → MEMBERSHIP_GAP.
3. Privacy-budget posture — DP disabled, epsilon >= 80% of cap, or
   aggregate constraints absent → PRIVACY_RISK.
4. Analysis-template SQL validity — unresolved parameters, dangling
   configured-table aliases, invalid columns → CONFIG_GAP.
5. Protected-query output configuration — missing S3 receiver,
   cross-account bucket policy widening → CONFIG_GAP.
6. Configured-audience readiness — model not READY, stale training
   data, missing destination → CONFIG_GAP.
7. Aggregation — worst finding wins by precedence
   (MEMBERSHIP_GAP > PRIVACY_RISK > CONFIG_GAP > OK).

Emits a deterministic VERDICT per collaboration:

```text
COLLABORATION: <collaboration-id or ARN>
VERDICT: MEMBERSHIP_GAP | PRIVACY_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and rule number>
FINDINGS:
  - [MEMBERSHIP_GAP] <finding description (Rule Mn)>
  - [PRIVACY_RISK] <finding description (Rule Pn)>
  - [CONFIG_GAP] <finding description (Rule An/Qn/Cn)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Clean Rooms collaboration snapshot and ask any of:

- "audit this Clean Rooms collaboration"
- "check member activation status"
- "is differential privacy enabled on this collaboration?"
- "how much epsilon budget is left?"
- "validate the analysis template SQL"
- "is the configured audience model trained?"
- "why are protected queries failing?"
- "is this collaboration ready for production?"

A bare collaboration ARN or ID + any audit verb ("audit this
collaboration", "check collaboration health") also routes here via the
orchestrator.

## Inputs

- A Clean Rooms collaboration configuration snapshot, pasted inline
  or referenced by file path. The snapshot should include:
  - Collaboration metadata (status, creatorDisplayName,
    queryLogStatus, analyticsEngine, configuredAudienceModelArn).
  - Member list with status and abilities.
  - Differential privacy config (enabled, epsilonBudgetPerMember).
  - Per-member epsilon spend (summed from ListProtectedQueries).
  - Configured tables with allowedColumns, analysisRuleType, and
    aggregateConstraints.
  - Analysis template bodies with parameters.
  - Configured audience model state (from cleanroomsml
    get-configured-audience-model).
- For live-account audits: a collaboration ARN or ID — the skill
  emits the AWS CLI commands to retrieve the full configuration.

## Outputs

- One VERDICT block per collaboration (multiple findings aggregate to
  the worst verdict by precedence).
- Enumerated FINDINGS list with per-finding rule citation
  (M1-M4, P1-P4, A1-A4, Q1-Q2, C1-C3).
- Specific remediation: activate members, enable DP, add aggregate
  constraints, recreate analysis templates, retrain audience models.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Audit specialist for Clean Rooms Analytics).
- `/aws:audit-iam-least-privilege` for IAM analysis of the Clean
  Rooms service roles that members use to access configured tables.
- `/aws:audit-s3-public-access` for auditing the S3 buckets that
  receive protected-query output — a public bucket silently widens
  the audience for the privacy-controlled result set.
