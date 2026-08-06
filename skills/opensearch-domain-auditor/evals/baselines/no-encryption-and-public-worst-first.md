# Baseline (no-skill) response: no-encryption-and-public-worst-first

This file captures what a generic assistant produces WITHOUT the
opensearch-domain-auditor skill loaded.

---

This domain has multiple serious problems. Encryption at rest is disabled,
so all data on disk is plaintext. The access policy grants es:ESHttp* to
Principal "*" with no condition, which means anyone with AWS credentials
can read and write all data via the REST API. Node-to-node encryption is
also off, HTTPS is not enforced, FGAC is disabled, and no slow logs are
published.

You should enable encryption, restrict the access policy, enable node-to-
node encryption, and turn on FGAC. This domain needs significant hardening
before it can be used for any sensitive data.
