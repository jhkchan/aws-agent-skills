# Baseline (no-skill) response: permissive-scp-security-service-disable

This file captures what a generic assistant produces WITHOUT the
organizations-scp-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, OU-hierarchy reasoning).

---

The organization has LeaveOrganization denied at the root level, which
is good practice. FullAWSAccess is present.

However, the SCPs do not deny actions like
guardduty:DeleteDetector, securityhub:DisableSecurityHub,
config:DeleteConfigurationRecorder, or cloudtrail:DeleteTrail. This
means if an attacker compromises an account, they could disable your
detection services before exfiltrating data.

You should add a deny SCP for these security service disruption
actions at the root level.
