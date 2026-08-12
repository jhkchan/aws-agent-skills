# Baseline (no-skill) response: cross-account-secret-access-denied

This file captures what a generic assistant produces WITHOUT the
secrets-manager-rotation-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, symptom-to-layer triage).

---

The Lambda is getting AccessDenied when calling GetSecretValue. The
rotation role in account 222222222222 needs permission to read the
secret in account 111111111111. Add a policy to the rotation role
granting `secretsmanager:GetSecretValue` on the secret ARN.

If that's already in place (it looks like it is), the issue might be
KMS — Secrets Manager uses KMS to decrypt the secret value, and the
key policy on the customer-managed CMK might not allow the cross-
account role. Check the KMS key policy and add the rotation role ARN
to it.
