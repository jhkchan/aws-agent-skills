# Baseline (no-skill) response: batch-write-migration

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, BatchWriteItem pattern,
UnprocessedItems handling, exponential backoff recommendation).

---

Your DynamoDB table is experiencing occasional throttling because you're
making 1,200 individual PutItem calls per second. Even though your
partition key is well-distributed, the sheer number of requests is
overwhelming your connection pool.

You should switch to using BatchWriteItem, which lets you write up to
16 items in a single request. This will reduce your request count by
16x:

```python
with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)
```

You should also add exponential backoff with jitter to handle any
retries. The AWS SDK does this by default, but you might want to
configure custom retry settings for your high-volume use case.
