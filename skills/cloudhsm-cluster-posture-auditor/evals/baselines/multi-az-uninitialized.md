# Baseline (no-skill) response: multi-az-uninitialized

This file captures what a generic assistant produces WITHOUT the
cloudhsm-cluster-posture-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, cluster-initialization reasoning).

---

The cluster has 3 HSMs across 3 AZs with recent backups, which looks
like a solid setup. However, the cluster state shows UNINITIALIZED,
which means you still need to run the InitializeCluster process.

You should download the cluster CSR, sign it with your CA, and upload
the signed certificate. Also the CO password has not been changed yet,
so make sure to do that after initialization.

The security group is properly scoped.
