# Baseline (no-skill) — enhanced-fanout-registration

> This is the response a model produces **without** the skill
> definition. It creates the stream but misses the enhanced fan-out
> consumer registration step, the SubscribeToShard API requirement,
> the consumer ARN in IAM Resource lists, the max-20-consumer limit,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the stream:

```bash
aws kinesis create-stream --stream-name clickstream --shard-count 10
```

Then have your consumers read from it with GetRecords.
