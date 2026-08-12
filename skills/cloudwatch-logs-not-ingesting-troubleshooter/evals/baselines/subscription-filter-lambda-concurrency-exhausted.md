# Baseline (no-skill) response: subscription-filter-lambda-concurrency-exhausted

---

Your Lambda destination is hitting the account concurrency limit
under load, which is causing dropped invocations from the subscription
filters. You can set reserved concurrency on the destination function
to guarantee it gets capacity:

```
aws lambda put-function-concurrency \
  --function-name fn-subscription-filter-lambda-concurrency-exhausted \
  --reserved-concurrent-executions 500
```

You may also want to reduce the number of subscription filters fanning
out to the same function, or request a concurrency quota increase from
AWS Support.
