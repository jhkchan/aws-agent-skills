# Baseline (no-skill) response: stale-95-days

This file captures what a generic assistant produces WITHOUT the
resiliencehub-app-assessment-auditor skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, staleness-first
precedence, enumerated FINDINGS, specific remediation with CLI).

---

This Resilience Hub app has a compliance score of 85 which looks pretty
good. Most of the components are compliant with the policy. There's one
component (reporting-job) that is not compliant but it's in the Standard
tier so it's probably not critical.

The assessment was run a few months ago. You should probably re-run it
to get fresh data. The policy looks reasonable with MissionCritical at
5 min RTO/RPO.

I'd say this app is in decent shape overall. Maybe address the one
non-compliant component when you get a chance.
