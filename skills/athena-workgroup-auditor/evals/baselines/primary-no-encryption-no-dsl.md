# Baseline (no-skill) response: primary-no-encryption-no-dsl

This file captures what a generic assistant produces WITHOUT the
athena-workgroup-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, blast-radius reasoning).

---

This Athena workgroup called `primary` has enforcement disabled and no
encryption or data scan limit configured. You should enable
EnforceWorkGroupConfiguration and configure encryption on the result
location. The lack of a scan limit means queries could get expensive.

The primary workgroup is a default one that AWS creates for you. It
usually has weaker settings so it is worth locking down.
