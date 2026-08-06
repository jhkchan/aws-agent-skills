# Baseline (no-skill) response: enforce-off-configs-advisory

This file captures what a generic assistant produces WITHOUT the
athena-workgroup-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, blast-radius reasoning).

---

This ETL workgroup has SSE-KMS encryption and a 1 TB scan limit
configured, which looks healthy. However, EnforceWorkGroupConfiguration
is false. That setting controls whether the workgroup config overrides
what callers send in StartQueryExecution. You may want to flip it to
true so the controls are actually applied.
