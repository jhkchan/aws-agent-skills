# Baseline (no-skill) response: multi-az-default-co-password

This file captures what a generic assistant produces WITHOUT the
cloudhsm-cluster-posture-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, CO-password reasoning).

---

This cluster looks well configured — 3 HSMs across 3 AZs, recent backups
with 90-day retention, cluster initialized, and a properly scoped security
group.

One thing to check is that the CO password has not been changed from the
default. You should change the default admin password to something secure
as soon as possible since the default is publicly known.
