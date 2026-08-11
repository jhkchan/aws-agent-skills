# Baseline (no-skill) response: snapstart-enablement

This file captures what a generic assistant produces WITHOUT the
lambda-cold-start-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, SnapStart CLI
sequence with versioned alias, latency impact estimate, CONFIRM gate).

---

Your Java Lambda function has high cold-start latency. The init phase
is taking about 3.2 seconds, which is typical for Spring Boot on Java.
Since you're using Java 21, you should enable SnapStart, which caches
the initialized JVM and restores it on cold start instead of
re-initializing from scratch.

You can enable it with:

```
aws lambda update-function-configuration --function-name fn-snapstart-enablement --snap-start '{"ApplyOn":"PublishedVersions"}'
```

This should reduce your init time significantly. You'll also need to
publish a new version and point your alias at it.
