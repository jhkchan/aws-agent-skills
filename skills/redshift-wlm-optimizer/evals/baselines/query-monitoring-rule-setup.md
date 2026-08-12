# Baseline (no-skill) response: query-monitoring-rule-setup

This file captures what a generic assistant produces WITHOUT the
redshift-wlm-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, QMR metric threshold math,
log-then-abort progression, STL_QUERY_METRICS citation, CONFIRM gate).

---

Your cluster is getting hit by runaway queries. The CPU is at 99% p95
and some analyst queries are taking 300 seconds. The p99 query execution
time is 37x the median, which suggests a few bad queries are dominating
the cluster.

You should set up Query Monitoring Rules (QMR) to catch these. You can
create rules in your WLM configuration that will abort queries that
exceed certain thresholds.

For example, you could add a rule like this:

```json
{"rule_name": "long-query", "predicate": "query_execution_time > 300000000", "action": "abort"}
```

This would abort any query that runs longer than 300 seconds. You might
also want to add a rule for CPU time.

After setting these up, the runaway queries should get killed before
they impact the rest of the cluster.
