# Baseline (no-skill) response: appconfig-terminated-deployment-recovery

This file captures what a generic assistant produces WITHOUT the
appconfig-deployment-operator skill loaded.

---

It looks like your deployment was terminated because the
configuration profile was deleted. You can try to resume the
deployment with:

```
aws appconfig start-deployment \
  --application-id abc123 \
  --environment-id env-456 \
  --deployment-strategy-id linear-20-percent-30min-bake \
  --configuration-profile-id prof-789-restored \
  --configuration-version 9
```

This should pick up where the previous deployment left off. If
that doesn't work, you may need to contact AWS support.
