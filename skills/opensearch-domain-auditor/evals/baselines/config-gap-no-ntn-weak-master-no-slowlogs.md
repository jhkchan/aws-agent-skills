# Baseline (no-skill) response: config-gap-no-ntn-weak-master-no-slowlogs

This file captures what a generic assistant produces WITHOUT the
opensearch-domain-auditor skill loaded.

---

This domain has customer-managed KMS encryption and FGAC enabled, which is
good. However there are several configuration gaps:

- Node-to-node encryption is off — traffic between OpenSearch nodes is
  plaintext.
- The dedicated master nodes are t3.small.search, which is burstable and
  may not be sufficient under load. Consider upgrading to m5.large.search.
- The cluster is not zone-aware — all nodes are in a single AZ.
- Slow logs are not being published to CloudWatch Logs.

You should address these gaps to improve the security and operational
posture of the domain.
