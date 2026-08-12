# Baseline (no-skill) response: trail-logging-disabled

---

Your CloudTrail trail shows `isLogging: false`. You need to start
logging on it:

```
aws cloudtrail start-logging --name prod-audit-trail
```

The trail was created but never started. Make sure to call
`start-logging` after creating a trail.
