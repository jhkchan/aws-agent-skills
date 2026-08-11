# Baseline (no-skill) response: init-phase-refactor

This file captures what a generic assistant produces WITHOUT the
lambda-cold-start-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, global-scope pattern
with runtime-specific code, latency impact estimate, CONFIRM gate).

---

Your Python function is slow because you're creating new database
connections and boto3 clients inside the handler on every invocation.
This adds 200-500 ms of TLS overhead each time. You should move these
to global scope so Lambda reuses them across invocations.

Instead of:

```python
def handler(event, context):
    client = boto3.client('dynamodb')
    db = psycopg2.connect(...)
```

Do:

```python
client = boto3.client('dynamodb')
db = psycopg2.connect(...)

def handler(event, context):
    # use client and db here
```

This should reduce your per-invocation latency significantly.
