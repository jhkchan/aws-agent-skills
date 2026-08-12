# Baseline (no-skill) response: dnssec-ds-record-mismatch

This file captures what a generic assistant produces WITHOUT the
route53-dns-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

The SERVFAIL error from some resolvers suggests a DNSSEC problem. You
should check that DNSSEC is configured correctly in Route 53. Try
disabling DNSSEC and see if that fixes the issue.

The fact that it works on Google DNS but not Cloudflare means the
problem is with DNSSEC validation. You might need to update your
DNSSEC settings or contact your registrar.
