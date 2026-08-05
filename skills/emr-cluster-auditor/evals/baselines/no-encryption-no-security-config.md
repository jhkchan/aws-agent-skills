# Baseline (no-skill) response: no-encryption-no-security-config

This file captures what a generic assistant produces WITHOUT the
emr-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, encryption-plane reasoning).

---

This EMR cluster does not have a SecurityConfiguration attached, which means
no encryption settings are configured. You should create a security
configuration with encryption enabled and attach it to your cluster.

The cluster also has VisibleToAllUsers set to true, which means all IAM
users in the account can access it. Consider setting this to false.

To fix this, create a security configuration in the EMR console or CLI with
S3 encryption, local disk encryption, and in-transit encryption enabled, then
recreate the cluster with that configuration.
