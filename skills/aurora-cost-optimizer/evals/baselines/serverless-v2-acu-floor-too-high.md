# Baseline (no-skill) response: serverless-v2-acu-floor-too-high

This file captures what a generic assistant produces WITHOUT the
aurora-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, ACU floor savings math,
SLA confirmation gate before tuning MinCapacity, anti-pattern: don't
drop floor below cold-start SLA).

---

Your Serverless v2 cluster has MinCapacity=8 but CPU averages 8% and
the ACU sits at 4.5 most of the time. You can probably lower the
MinCapacity to save money. Try changing MinCapacity to 2 and see if
the cluster still handles your traffic.

Note that lowering the minimum might affect cold-start latency.
