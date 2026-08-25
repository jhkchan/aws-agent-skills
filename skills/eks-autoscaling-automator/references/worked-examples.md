# Worked Examples (load on demand) — EKS Autoscaling Automator

Secondary worked examples moved verbatim from SKILL.md; the primary example remains inline in SKILL.md. Loaded on demand.

---

## Worked example — REVIEW_REQUIRED (moved from SKILL.md)

```text
AUTOSCALING: staging-cluster-autoscaling
CLUSTER: EKS 1.28, 8 nodes
TOOLING: NONE | NONE | NOT INSTALLED
VERDICT: REVIEW_REQUIRED
GAP: (1) metrics-server not installed — HPA cannot function. (2) No HPA configured. (3) No PDBs. (4) On-demand only — cost savings available. (5) No overprovisioning — 2-5 min scale-up latency.
TEMPLATE: (blocked until metrics-server installed)
```
