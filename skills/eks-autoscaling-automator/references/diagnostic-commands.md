# Diagnostic Commands (load on demand) — EKS Autoscaling Automator

Pre-flight, diagnostic, and verification command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE** before any state-changing operation.
- **Before CA→Karpenter migration:** scale workloads with 20% headroom,
  uninstall CA, wait 10 min, install Karpenter, verify NodeClaims.
- **Before `WhenEmptyOrUnderutilized`:** run `WhenEmpty` for 1 week.
- **Before descheduler in prod:** run in DryRun for 24h.
- **For spot clusters:** verify SQS interruption queue receives events.
