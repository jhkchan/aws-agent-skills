# Baseline (no-skill) response: ec2-imdsv2-resolved-stale-cache

This file captures what a generic assistant produces WITHOUT the
securityhub-finding-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, standard-driven probe
order).

---

If the finding shows RESOLVED, you're fine. Security Hub just takes a
while to clean up old findings — they hang around for a few days
before disappearing from the console. The instance itself is fixed,
so you can close the ticket.

If you want it to disappear faster, you can archive the finding
manually in the Security Hub console.
