# Baseline (no-skill) — missing-deduplication-config

> This is the response a model produces **without** the skill
> definition. It creates the queue without any deduplication
> method, does not flag the missing prerequisite, and does not
> emit a PREREQUISITES_MISSING verdict. Generated for with-
> skill-vs-baseline comparison.

---

Create the queue:

```bash
aws sqs create-queue \
  --queue-name events.fifo \
  --attributes "FifoQueue=true,ContentBasedDeduplication=false"
```

Producers can just send messages.
