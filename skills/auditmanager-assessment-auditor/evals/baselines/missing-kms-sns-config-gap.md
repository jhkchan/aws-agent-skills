# Baseline (no-skill) response: missing-kms-sns-config-gap

This file captures what a generic assistant produces WITHOUT the
auditmanager-assessment-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, evidence-integrity reasoning,
data-source dependency chain, per-verdict remediation).

---

The SOC 2 assessment is in good shape with 88% compliance (132 of 150
controls passing). Evidence collection is working well with only 8
NOT_ASSESSED controls.

However, I notice that the KMS key and SNS topic are not configured in the
settings. You should consider setting these up — the KMS key provides
encryption for your assessment data, and the SNS topic sends notifications
about collection events.

The process owners and assessment reports destination are configured, so
just the encryption and notification settings need attention.
