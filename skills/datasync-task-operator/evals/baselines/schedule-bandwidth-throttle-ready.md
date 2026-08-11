# Baseline (no-skill) response: schedule-bandwidth-throttle-ready

This file captures what a generic assistant produces WITHOUT the
datasync-task-operator skill loaded.

---

To add a daily schedule with bandwidth throttle to your task:

```bash
aws datasync update-task \
  --task-arn arn:aws:datasync:us-east-1:111111111111:task/task-001 \
  --schedule-expression "rate(1 day)"
```

For the bandwidth throttle, you might also pass an options JSON:

```bash
aws datasync update-task \
  --task-arn arn:aws:datasync:us-east-1:111111111111:task/task-001 \
  --options '{"BandwidthLimitInMb": 1000}'
```

The schedule will fire daily and the throttle will cap throughput at
1000 Mb/s.
