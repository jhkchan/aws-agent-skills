# Baseline (no-skill) response: trail-stopped-inadvertently

This file captures what a generic assistant produces WITHOUT the
cloudtrail-gap-troubleshooter skill loaded.

---

Your trail is stopped. The status shows IsLogging: false, which means
the trail was explicitly stopped. You can restart it by going to the
CloudTrail console and clicking "Start logging", or run:

```
aws cloudtrail start-logging --name corp-trail
```

After that, check the status again to make sure it's logging. You
should also look at who stopped it — the StopLogging event in CloudTrail
event history should tell you which user or role did it.

Consider adding an alarm so you know if it stops again.
