# Baseline (no-skill) response: config-gap-unsupported-condition-key

This file captures what a generic assistant produces WITHOUT the
organizations-scp-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, OU-hierarchy reasoning).

---

The organization has good guardrails in place: LeaveOrganization is
denied, security service disruption is denied, and FullAWSAccess is
present. There is also a DenyKmsOutsideLambda SCP that denies KMS
Decrypt and GenerateDataKey when the ViaService is Lambda.

Wait — actually, the intent of that SCP seems to be to block KMS
decryption unless it comes from Lambda. The condition uses
kms:ViaService with StringEquals to lambda.us-east-1.

The other guardrails look fine. The KMS SCP might need review to make
sure it is working as intended.
