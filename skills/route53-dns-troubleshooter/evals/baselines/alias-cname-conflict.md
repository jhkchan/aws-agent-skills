# Baseline (no-skill) response: alias-cname-conflict

This file captures what a generic assistant produces WITHOUT the
route53-dns-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

You can't create the ALIAS record because there's already a CNAME
record for the same domain name. You'll need to delete the existing
CNAME record first before creating the new ALIAS record.

In the Route 53 console, find the existing CNAME record for
api.example.com, delete it, and then create your new ALIAS record.
