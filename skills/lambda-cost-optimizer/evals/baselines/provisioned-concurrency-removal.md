# Baseline (no-skill) response: provisioned-concurrency-removal

This file captures what a generic assistant produces WITHOUT the
lambda-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, idle-compute dollar math,
CONFIRM gate, latency-impact warning).

---

Your function `fn-provisioned-concurrency-removal` has 10 provisioned
concurrency but is only receiving about 0.6 invocations per minute. That
means most of the provisioned capacity is sitting idle. You're paying
for 10 concurrent executions whether or not they're being used.

Since this is a batch report generator that isn't latency-sensitive, you
could probably remove the provisioned concurrency and just use on-demand
invocations. That would save you money on the idle compute.

You can remove it with:

```
aws lambda delete-provisioned-concurrency-config --function-name fn-provisioned-concurrency-removal --qualifier prod
```

Just note that cold starts will come back, so the first invocation of
each report may take a couple seconds longer.
