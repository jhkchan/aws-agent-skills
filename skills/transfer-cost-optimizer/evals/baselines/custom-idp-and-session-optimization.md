# Baseline (no-skill) response: custom-idp-and-session-optimization

This file captures what a generic assistant produces WITHOUT the
transfer-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, per-auth Lambda cost math,
auth-caching recommendation, session-pattern analysis, CONFIRM gate).

---

Your Transfer Family server uses a custom Lambda identity provider via
API Gateway. With 80,000 session starts per month, that's 80,000 Lambda
invocations and 80,000 API Gateway requests. Since auth caching isn't
configured, every session start triggers a fresh authentication.

The Lambda cost is probably around $10-15/month (80K invocations × 250ms
at the Lambda pricing rate), plus API Gateway costs. It's not huge, but
you could reduce it by enabling auth caching so repeated logins within
a short window don't re-invoke the Lambda.

Also, your average session is 45 minutes but only transfers 0.6 files.
That means most sessions are partners connecting, checking for files,
and disconnecting without transferring anything. You might want to
investigate whether those sessions can be shorter.

For auth caching, you'd need to update your Lambda function to cache
authentication results for a few minutes:

```python
# Pseudocode for caching in the Lambda
cache = {}
def lambda_handler(event, context):
    username = event["username"]
    if username in cache and not expired(cache[username]):
        return cache[username]["response"]
    # ... authenticate ...
    cache[username] = {"response": result, "timestamp": now()}
    return result
```

This would cut Lambda invocations significantly for repeat logins.
