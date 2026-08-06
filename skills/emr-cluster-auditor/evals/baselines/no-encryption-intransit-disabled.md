# Baseline (no-skill) response: no-encryption-intransit-disabled

This file captures what a generic assistant produces WITHOUT the
emr-cluster-auditor skill loaded.

---

The cluster has a security configuration with S3 and local disk encryption
enabled, but in-transit encryption is not configured. This means that
communication between nodes in the cluster is not encrypted.

You should update your security configuration to include in-transit encryption
with a TLS certificate. This requires providing a PEM certificate chain and
private key.

The S3 and local disk encryption settings look good with SSE-KMS configured.
