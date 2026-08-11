# Baseline (no-skill) — missing-stream-mode

> This is the response a model produces **without** the skill
> definition. It creates the stream with a default shard count without
> flagging that the stream mode (provisioned vs on-demand) is a
> critical prerequisite decision, and does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here's the command:

```bash
aws kinesis create-stream --stream-name app-events --shard-count 1
```

You can adjust later if you need more capacity.
