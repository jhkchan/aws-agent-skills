# Baseline (no-skill) response: missing-waf-and-logging

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, defense-in-depth reasoning).

---

This distribution has good TLS settings (TLS 1.2 2021) and OAC is configured
on the S3 origin. However, there is no WAF Web ACL associated and logging
is disabled.

You should consider adding a WAF to protect against common web attacks and
enabling access logging for monitoring and compliance purposes.

The geo restrictions and viewer protocol policy look fine.
