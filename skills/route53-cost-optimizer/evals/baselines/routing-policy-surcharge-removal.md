# Baseline (no-skill) response: routing-policy-surcharge-removal

This file captures what a generic assistant produces WITHOUT the
route53-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, per-billion surcharge math,
routing policy evaluation, CONFIRM gate).

---

Since all your traffic is from us-east-1, latency-based routing probably
isn't doing much. You could switch to simple routing to save on the
query surcharge.

Change the routing policy in your Route 53 records from latency-based to
simple or weighted. Latency routing costs extra per query.

The exact savings depend on the surcharge rate, but with 200M queries
you should save something per month.
