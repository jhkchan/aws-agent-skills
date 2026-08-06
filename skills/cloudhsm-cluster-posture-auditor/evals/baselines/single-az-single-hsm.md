# Baseline (no-skill) response: single-az-single-hsm

This file captures what a generic assistant produces WITHOUT the
cloudhsm-cluster-posture-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, AZ-distribution reasoning).

---

This CloudHSM cluster has a single HSM in us-east-1a. That means if the
AZ goes down, you lose access to all your keys. You should probably add
more HSMs in other AZs for high availability.

The backup retention policy is set to 0 days, which means backups are
not being kept. You should change this to at least 90 days.

The cluster is initialized and the CO password has been changed, which
is good. The security group looks properly scoped.
