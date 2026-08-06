# Baseline (no-skill) response: public-access-wildcard-http

This file captures what a generic assistant produces WITHOUT the
opensearch-domain-auditor skill loaded.

---

The access policy for this OpenSearch domain grants es:ESHttp* to Principal
"*" with no condition, which means anyone with AWS credentials can read and
write data via the OpenSearch REST API. This is a serious exposure.

You should restrict the principal to specific IAM roles or accounts, or add
a condition like aws:SourceIp to limit access.

The domain has encryption at rest and node-to-node encryption enabled, which
is good. Fine-grained access control is off — you may want to enable it for
additional per-index controls.
