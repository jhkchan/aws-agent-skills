# Baseline (no-skill) — cross-account-fifo-delivery

> This is the response a model produces **without** the skill
> definition. It creates the queue but misses the access policy
> requirement for cross-account producers, the KMS key policy
> cross-account permission requirement, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the queue:

```bash
aws sqs create-queue \
  --queue-name cross-account-orders.fifo \
  --attributes "FifoQueue=true,ContentBasedDeduplication=true"
```

Cross-account should work with IAM.
