# Baseline (no-skill) response: circular-dependency-detected

This file captures what a generic assistant produces WITHOUT the
event-driven-automator skill loaded.

---

The proposed workflow looks fine. Lambda-B publishes audit events
which trigger Lambda-D, and Lambda-D publishes user events which
trigger Lambda-B.

To set this up, configure both Lambdas to publish events to the
custom bus. The existing rules will pick up the events.

```
aws events put-targets ...
```

You should add a DLQ to each Lambda target.
