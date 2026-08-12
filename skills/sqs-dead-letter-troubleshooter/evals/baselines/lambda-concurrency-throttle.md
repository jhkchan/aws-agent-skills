# Baseline (no-skill) response: lambda-concurrency-throttle

---

Your SQS queue backlog is growing and the DLQ is filling. The Lambda has
no errors but it seems like it can't keep up. The reserved concurrency
is 5, which might be too low. You should increase the reserved
concurrency to allow more parallel processing. Also check if the account
has enough overall concurrency available.

After fixing the concurrency, you can redrive the DLQ messages back to
the source queue.
