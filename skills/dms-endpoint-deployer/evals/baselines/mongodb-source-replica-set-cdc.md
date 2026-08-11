# Baseline (no-skill) — mongodb-source-replica-set-cdc

> This is the response a model produces **without** the skill
> definition. It creates the MongoDB endpoint but misses the replica
> set requirement for CDC (standalone does not support CDC), the
> extra connection attributes (NestingLevel, ExtractDocId,
> DocsToInvestigate), and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To create a DMS MongoDB source endpoint:

1. Create a MongoDB source endpoint in DMS.
2. Enter the server and port.
3. Provide credentials.
4. Enable CDC in the task.

```bash
aws dms create-endpoint --engine-name docdb --server-name mongo-prod \
  --port 27017
```

MongoDB CDC should work out of the box.
