# Baseline (no-skill) response: no-process-owners-config-gap

This file captures what a generic assistant produces WITHOUT the
auditmanager-assessment-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, evidence-integrity reasoning,
data-source dependency chain, per-verdict remediation).

---

The ISO 27001 assessment looks healthy at 92% compliance with only 3
failing controls. Evidence collection is working properly.

The settings have a KMS key, SNS topic, and assessment reports destination
configured. However, the defaultProcessOwners list is empty. You should
assign at least one reviewer role so that evidence requiring human
attestation has an owner to review and approve it.

Without process owners, any UNDER_REVIEW controls will not have a
designated reviewer to close them out.
