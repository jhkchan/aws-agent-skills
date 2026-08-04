# Baseline (no-skill) response: insecure-origin-protocol

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, origin-traffic reasoning).

---

This distribution uses a custom origin with http-only protocol policy. This
means CloudFront connects to the origin over HTTP which is not encrypted.

The viewer side looks good with TLS 1.2 2021 and https-only. There is a WAF
and logging is enabled. You should change the origin protocol to https-only
to encrypt traffic between CloudFront and your origin.
