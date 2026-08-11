# Baseline (no-skill) — provisioned-shard-sizing

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the shard count sizing
> formula (max of data and record dimensions), the provisioned mode
> stream-mode-details requirement, the standard GetRecords IAM policy
> actions (GetShardIterator, DescribeStream), the
> WriteProvisionedThroughputExceeded alarm, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the stream with some shards:

```bash
aws kinesis create-stream --stream-name events-stream --shard-count 4
```

Then set up your producer and consumer. You can adjust shards later if
needed.
