# Baseline (no-skill) response: sg-common-full-coverage-ok

This file captures what a generic assistant produces WITHOUT the
firewall-manager-compliance-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, the OK-baseline enumeration,
defense-in-depth notes).

---

This SECURITY_GROUPS_COMMON policy is in READY state with remediation enabled.
It applies a baseline security group (baseline-sg-prod) across EC2 instances,
ENIs, and both ALB and CLB load balancers org-wide.

The policy is protecting 612 resources with 0 non-compliant. DeleteUnusedFMSPolicies
is enabled which is good hygiene. The SNS notification channel (fms-alerts) is
configured.

This looks like a healthy configuration. No changes needed.
