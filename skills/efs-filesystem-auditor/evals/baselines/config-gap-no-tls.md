# Baseline (no-skill) response: config-gap-no-tls

This file captures what a generic assistant produces WITHOUT the
efs-filesystem-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, TLS-enforcement-as-config-gap reasoning).

---

This filesystem is encrypted and has a lifecycle policy and an access
point. The filesystem policy is scoped to a specific same-account role
which is good practice.

However, the policy does not include any condition requiring secure
transport. This means clients could potentially mount without TLS, sending
NFS traffic in plaintext. You might want to add a aws:SecureTransport
condition to the policy to enforce encryption in transit.

Overall this is a reasonably configured filesystem with a minor gap in
transport encryption enforcement.
