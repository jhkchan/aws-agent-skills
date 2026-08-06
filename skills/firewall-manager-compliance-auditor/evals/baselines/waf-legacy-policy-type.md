# Baseline (no-skill) response: waf-legacy-policy-type

This file captures what a generic assistant produces WITHOUT the
firewall-manager-compliance-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, the WAF-vs-WAFv2 legacy
distinction, migration-path remediation).

---

This Firewall Manager policy is using WAF (the original WAF service) and is in
READY state with remediation enabled. It covers 18 resources in account
111111111111 with 0 non-compliant.

The policy looks healthy — WAF is protecting your resources and there are no
violations. WAF and WAFv2 are both supported by FMS so you can use either
depending on which WebACL technology you've standardized on.

No changes needed.
