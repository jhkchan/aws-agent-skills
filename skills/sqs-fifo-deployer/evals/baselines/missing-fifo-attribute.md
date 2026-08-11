# Baseline (no-skill) — missing-fifo-attribute

> This is the response a model produces **without** the skill
> definition. It attempts to create the queue without the .fifo
> suffix, does not flag the missing prerequisite, and does not
> emit a PREREQUISITES_MISSING verdict. Generated for with-
> skill-vs-baseline comparison.

---

Create the queue:

```bash
aws sqs create-queue \
  --queue-name my-queue \
  --attributes "FifoQueue=true"
```

Should be fine.
