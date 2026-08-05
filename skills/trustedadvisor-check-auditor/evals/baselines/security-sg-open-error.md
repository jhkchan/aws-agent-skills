# Baseline (no-skill) response: security-sg-open-error

This file captures what a generic assistant produces WITHOUT the
trustedadvisor-check-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, support-tier awareness, staleness checking).

---

This Trusted Advisor check shows that security group
sg-security-sg-open-error has port 22 (SSH) open to 0.0.0.0/0. This is a
security risk because it allows SSH access from any IP address on the
internet.

You should restrict the security group to only allow SSH from known IP
ranges. The account has Business support so all checks should be
available.

To fix this, update the security group inbound rules to use a more
restrictive CIDR block.
