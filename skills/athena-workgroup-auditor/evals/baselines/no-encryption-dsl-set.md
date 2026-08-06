# Baseline (no-skill) response: no-encryption-dsl-set

This file captures what a generic assistant produces WITHOUT the
athena-workgroup-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, blast-radius reasoning).

---

This ad-hoc workgroup is enforced and has a 1 TB scan limit, but there
is no EncryptionConfiguration on the ResultConfiguration. That means
query results written to the OutputLocation bucket are stored as
plaintext objects. Anyone with s3:GetObject on that prefix can read
the result sets. You should configure SSE-KMS (or at minimum SSE-S3)
on the workgroup's ResultConfiguration.
