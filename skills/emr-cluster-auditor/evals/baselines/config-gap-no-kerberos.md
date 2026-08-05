# Baseline (no-skill) response: config-gap-no-kerberos

This file captures what a generic assistant produces WITHOUT the
emr-cluster-auditor skill loaded.

---

The cluster has good encryption settings with all three layers enabled. The
IAM roles are scoped to specific buckets. Block Public Access is enabled.

However, Kerberos is not configured on this cluster. If you are processing
sensitive data, you should consider enabling Kerberos authentication. Also,
VisibleToAllUsers is set to true which is a deprecated flag — you should set
it to false to restrict access.

To enable Kerberos, you would need to recreate the cluster with Kerberos
attributes specified.
