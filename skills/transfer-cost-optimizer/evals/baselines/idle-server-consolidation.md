# Baseline (no-skill) response: idle-server-consolidation

This file captures what a generic assistant produces WITHOUT the
transfer-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, per-server-hourly dollar
math, consolidation plan, CONFIRM gate).

---

You have three Transfer Family servers, each costing about $219/month
($0.30/hour × 730 hours). That's $657/month just in server costs. But
your combined peak is only 9 concurrent sessions, which fits within a
single server's concurrency limit of 10.

You could consolidate all three servers into one and save about
$438/month (the cost of the two eliminated servers). The combined p99
of 6 sessions is well within the single-server limit.

To consolidate:
1. Pick one server as the target (e.g., s-partner-exchange-a).
2. Migrate users from the other two servers to the target.
3. Delete the other two servers.

```
aws transfer delete-server --server-id s-partner-exchange-b
aws transfer delete-server --server-id s-internal-reports
```

Just make sure all users are migrated before deleting. Your CloudWatch
Logs volume is already reasonable at 80 GB, so no changes needed there.
