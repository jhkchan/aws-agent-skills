# Error Handling (load on demand) — DynamoDB Throttling Optimizer

Error-handling deep dives and API failure tables, moved verbatim from SKILL.md.


---

## Step 6: UnprocessedItems handling (moved from SKILL.md)

**UnprocessedItems handling:** BatchWriteItem may return unprocessed
items (throttled at partition level). The SDK's `batch_writer()`
automatically retries `UnprocessedItems` with exponential backoff.

---

## Step 7: Backoff with jitter pattern (moved from SKILL.md)

**Backoff with jitter pattern:**
```python
import time
import random

MAX_RETRIES = 10
BASE_DELAY = 0.05  # 50 ms

def write_with_backoff(write_fn, *args):
    for attempt in range(MAX_RETRIES):
        try:
            return write_fn(*args)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ProvisionedThroughputExceededException':
                raise
            # Full jitter: random between 0 and exponential delay
            delay = random.uniform(0, BASE_DELAY * (2 ** attempt))
            time.sleep(delay)
    raise Exception(f"Max retries ({MAX_RETRIES}) exceeded")
```
