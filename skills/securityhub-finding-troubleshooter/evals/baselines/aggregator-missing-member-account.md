# Baseline (no-skill) response: aggregator-missing-member-account

This file captures what a generic assistant produces WITHOUT the
securityhub-finding-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, standard-driven probe
order).

---

If findings aren't showing in the aggregator, you probably need to
re-invite the member account. Use the Security Hub console in the
aggregator account to invite 222222222222, then accept the
invitation in the member account.

Make sure both accounts are in the same Organization and that
Security Hub is enabled in both. Aggregation can take a few minutes
to sync.
