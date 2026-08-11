# Baseline (no-skill) response: appconfig-rollback-alarm-blocks

This file captures what a generic assistant produces WITHOUT the
appconfig-deployment-operator skill loaded.

---

You can start the deployment with:

```
aws appconfig start-deployment \
  --application-id abc123 \
  --environment-id env-456 \
  --deployment-strategy-id linear-20-percent-30min-bake \
  --configuration-profile-id prof-789 \
  --configuration-version 8
```

Note that your rollback alarm is currently in ALARM state. You
may want to investigate that before deploying, but the deployment
should still work. If the alarm keeps firing, AppConfig may roll
back automatically.
