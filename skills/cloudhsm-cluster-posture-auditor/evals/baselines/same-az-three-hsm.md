# Baseline (no-skill) response: same-az-three-hsm

This file captures what a generic assistant produces WITHOUT the
cloudhsm-cluster-posture-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, AZ-distribution reasoning).

---

This cluster has 3 HSMs which is good for redundancy. The backups are
recent and the retention policy is set to 90 days. The cluster is
initialized and the CO password has been changed.

One thing to note is that all 3 HSMs are in us-east-1a. If you want
better availability you might want to spread them across AZs, but having
3 HSMs should give you good hardware-level redundancy.

The security group is properly scoped to the application subnet.
