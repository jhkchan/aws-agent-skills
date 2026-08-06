# Baseline (no-skill) response: drifted-preventive-control

This file captures what a generic assistant produces WITHOUT the
controltower-control-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, drift-detection reasoning).

---

The Control Tower configuration looks mostly healthy. The landing zone is
active with version 3.3, and the controls show as SUCCEEDED.

However, the SCP verification shows that the
AWSControlTowerGuardrailRestrictedCommonPorts policy was modified — the
Deny on port 22 (SSH) was removed. This means SSH access is now allowed
even though the control shows as enabled.

You should review this SCP modification. If it was not intentional, you
can restore the original policy. The Config recorder is enabled and the
execution role is present, so the rest of the setup looks fine.
