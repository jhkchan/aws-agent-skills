# Baseline (no-skill) — on-demand-enhanced-fanout-sse

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the on-demand mode
> specifics (shard count irrelevance), the enhanced fan-out consumer
> registration flow, the SSE-KMS key policy requirement for the
> Kinesis service principal, the SubscribeToShard IAM requirement,
> the IteratorAge CloudWatch alarm threshold relative to retention,
> and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here's how to create a Kinesis stream:

1. Create the stream:
```bash
aws kinesis create-stream --stream-name telemetry-ingest --shard-count 1
```

2. Wait for it to be active, then start putting records.

3. You can add encryption in the console if needed.

That should work.
