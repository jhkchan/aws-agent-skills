# Baseline (no-skill) response: tune-tmd-completed

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-operator skill loaded.

---

To change the TreatMissingData setting on your alarm:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name prod-alb-availability \
  --treat-missing-data breaching
```

Wait, this will overwrite the existing alarm config — you need to
include all the other parameters. You may want to fetch the current
config first.

After updating, the alarm should now treat missing data as a breach
and fire when the metric stops reporting.
