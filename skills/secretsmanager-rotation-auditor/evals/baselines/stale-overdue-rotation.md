# Baseline (no-skill) response: stale-overdue-rotation

> This file captures what a generic assistant produces WITHOUT the
> secretsmanager-rotation-auditor skill loaded. The baseline notices
> the rotation is overdue but does not compute the overdue ratio, does
> not distinguish STALE from ROTATION_BROKEN, and misses the intermittent-
> failure root-cause analysis (check CloudWatch Logs for partial failures).

---

The last rotation for this DocumentDB secret was on May 1st, which is over
3 months ago. With a 30-day rotation interval, this is significantly overdue.
The Lambda function is active and the last invocation succeeded, so it's
unclear why the rotation hasn't happened recently.

You might want to trigger a manual rotation and then monitor the next
scheduled rotation to see if it succeeds automatically.

It's possible the EventBridge schedule has an issue or the rotation is
silently failing intermittently.
