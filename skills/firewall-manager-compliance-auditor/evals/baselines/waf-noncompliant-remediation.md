# Baseline (no-skill) response: waf-noncompliant-remediation

This file captures what a generic assistant produces WITHOUT the
firewall-manager-compliance-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, per-account drill-down).

---

This WAFv2 Firewall Manager policy is in READY state with remediation enabled.
There are 14 non-compliant resources across 3 accounts (4 in 111111111111, 8
in 222222222222, and 2 in 333333333333). The policy is protecting 86 resources
total.

Account 222222222222 has the most violations (8 out of 14) so you should
investigate that account first. The policy covers CloudFront, API Gateway,
ALB, and Web ACL resources.

You should look at each non-compliant resource and figure out why FMS couldn't
apply the WebACL. Common reasons are member-local overrides or missing
service-linked roles.
