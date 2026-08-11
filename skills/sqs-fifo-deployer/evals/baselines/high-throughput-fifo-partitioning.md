# Baseline (no-skill) — high-throughput-fifo-partitioning

> This is the response a model produces **without** the skill
> definition. It creates the queue but misses that
> DeduplicationScope and ThroughputLimit must BOTH be set
> together, the per-group deduplication scope change semantics,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the FIFO queue:

```bash
aws sqs create-queue \
  --queue-name high-throughput-events.fifo \
  --attributes "FifoQueue=true,DeduplicationScope=messageGroup"
```

That enables high throughput.
