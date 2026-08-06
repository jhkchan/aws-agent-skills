# Baseline (no-skill) response: tls-v1-allow-all

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, cipher-suite reasoning).

---

This CloudFront distribution has a couple of security issues. The TLS
minimum version is set to TLSv1 which is outdated. You should upgrade to
at least TLS 1.2.

The viewer protocol policy is set to allow-all which means HTTP is also
served. This should be changed to redirect-to-https or https-only.

The distribution has a WAF, logging, and geo restrictions configured which
is good. The S3 origin has an OAC configured as well.
