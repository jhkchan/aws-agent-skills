# Baseline (no-skill) — standard-fifo-with-dedup-and-dlq

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the FIFO DLQ
> requirement (Standard DLQ cannot attach to FIFO queue), the
> per-entity message group ID parallelism strategy, the
> visibility timeout vs consumer processing time relationship,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the queue:

```bash
aws sqs create-queue \
  --queue-name order-processing.fifo \
  --attributes "FifoQueue=true,ContentBasedDeduplication=true"
```

Then add a DLQ and you're good.
