# Baseline (no-skill) response: insecure-listener-tls10

This file captures what a generic assistant produces WITHOUT the
elbv2-load-balancer-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, TLS downgrade reasoning).

---

This ALB has an HTTPS listener on port 443 using the
ELBSecurityPolicy-TLS-1.0-2015-04 security policy. This policy supports TLS
1.0 which is considered outdated. You should consider upgrading to a newer
policy.

The load balancer looks fine otherwise — it has access logs enabled, a
security group allowing port 443, and healthy targets.
