# Baseline (no-skill) response: appconfig-linear-canary-start

This file captures what a generic assistant produces WITHOUT the
appconfig-deployment-operator skill loaded.

---

To start an AppConfig deployment, you can use
`aws appconfig start-deployment` with the application ID,
environment ID, and configuration profile ID. Here's roughly what
the command looks like:

```
aws appconfig start-deployment \
  --application-id abc123 \
  --environment-id env-456 \
  --deployment-strategy-id linear-20-percent-30min-bake \
  --configuration-profile-id prof-789 \
  --configuration-version 7
```

The deployment should take a few hours depending on the strategy.
You can check the status with `get-deployment`.
