# Baseline (no-skill) response: public-access-brokers

This file captures what a generic assistant produces WITHOUT the
msk-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, immutability-aware reasoning).

---

This MSK cluster has TLS encryption and IAM authentication enabled, and
logging is configured to both S3 and CloudWatch. However, public access
is enabled with SERVICE_PROVIDED_EIPS, which means the brokers are
accessible from the internet via Elastic IPs.

You should consider disabling public access if your clients can reach
the cluster through a VPN or VPC peering connection instead.
