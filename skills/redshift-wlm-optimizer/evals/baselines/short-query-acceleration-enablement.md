# Baseline (no-skill) response: short-query-acceleration-enablement

This file captures what a generic assistant produces WITHOUT the
redshift-wlm-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, SQA threshold tuning, queue
isolation math, CONFIRM gate, snapshot workflow).

---

Your short queries are waiting up to 45 seconds in the queue because
long aggregate reports are running at the same time. Since you're on
auto WLM with concurrency scaling, the basic WLM is already good. The
issue is that short queries are stuck in the same queue as long ones.

You could try enabling Short Query Acceleration (SQA). This will
automatically route short queries to a separate queue so they don't
have to wait behind long ones.

To enable SQA, update your parameter group:

```
aws redshift modify-cluster-parameter-groups --parameter-group-name mygroup --parameters ParameterName=wlm_json_configuration,ParameterValue='[{"auto_wlm":true,"concurrency_scaling":"auto","short_query_queue_enable":true}]'
```

This should help your point lookups complete faster.
