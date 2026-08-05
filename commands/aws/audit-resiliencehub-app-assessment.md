---
description: Audit an AWS Resilience Hub app assessment for staleness (>90 days), resiliency policy binding and tier calibration, per-tier RTO/RPO compliance breaches (MissionCritical/Critical NonCompliant), aggregate compliance score, app-version drift, failed/pending assessment status, and unimplemented alarm/SDD/test recommendations.
nl_triggers:
  - "audit this resilience hub assessment"
  - "is my app assessment stale"
  - "check RTO RPO compliance"
  - "resiliency policy coverage"
  - "assessment freshness check"
  - "app version drift resilience hub"
  - "compliance score too low"
  - "MissionCritical tier non compliant"
  - "resilience hub recommendations"
  - "resiliency policy not attached"
  - "resilience hub audit"
  - "failed assessment no data"
  - "resiliency posture check"
routes_to: resiliencehub-app-assessment-auditor
---

# /aws:audit-resiliencehub-app-assessment

Activate the `resiliencehub-app-assessment-auditor` skill and audit one
or more AWS Resilience Hub application assessments for assessment
freshness, policy binding, tier-aware compliance, and recommendation
coverage.

## What it does

Reads a Resilience Hub app-assessment snapshot (assessment metadata,
compliance map, resiliency policy, recommendation inventory) and applies
the ordered classification logic:

1. CONFIG_GAP — Failed/Pending/InProgress assessment status (no data),
   or no assessment has ever run.
2. STALE_ASSESSMENT — latest successful assessment older than 90 days.
3. App-version drift — assessment references an older appVersion than
   current (additive CONFIG_GAP finding).
4. Policy binding — no resiliency policy attached, or tier-to-RTO/RPO
   mapping is miscalibrated (additive CONFIG_GAP finding).
5. HIGH_RISK — any MissionCritical/Critical-tier component is
   NonCompliant, or complianceScore < 50 (systemic failure).
6. LOW_COMPLIANCE — complianceScore < 80 (and not HIGH_RISK).
7. Recommendation gaps — unimplemented Alarm recommendations contribute
   to CONFIG_GAP; SDD/Test gaps are informational.
8. OK — all dimensions pass, score >= 80, policy attached, no drift.

Emits a deterministic VERDICT per app:

```text
APP: <app-name or ARN>
VERDICT: STALE_ASSESSMENT | HIGH_RISK | LOW_COMPLIANCE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and finding>
FINDINGS:
  - <finding description (Step N)>
  - <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Resilience Hub assessment snapshot and ask any of:

- "audit this resilience hub assessment"
- "is my app assessment stale?"
- "check RTO/RPO compliance for this app"
- "what's the resiliency posture of this app?"
- "is the policy correctly calibrated?"

A bare app ARN + any audit verb also routes here via the orchestrator.

## Inputs

- An assessment snapshot including: assessment status (Success/Failed/
  Pending/InProgress), endTime, appVersion, complianceScore, compliance
  map (per-component tier + complianceStatus), resiliency policy (tiers
  with RTO/RPO), and recommendation inventory (Alarm/SDD/Test counts +
  implemented counts).
- For live-account audits: an app-ARN — the skill emits the AWS CLI
  commands to retrieve the full configuration.

## Outputs

- One VERDICT block per app (first matching step determines the verdict;
  worst finding wins across additive dimensions).
- Enumerated FINDINGS list with step citations.
- Specific remediation: re-run assessment, publish app version, attach
  policy, implement alarm recommendations, investigate NonCompliant
  components — all with CLI commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for resiliency and continuity).
- `/aws:audit-backup-plan` for auditing the backup and recovery posture
  that complements Resilience Hub assessments.
- `/aws:audit-cloudtrail-org-trail` for ensuring audit-trail integrity
  of resiliency-relevant API calls.
