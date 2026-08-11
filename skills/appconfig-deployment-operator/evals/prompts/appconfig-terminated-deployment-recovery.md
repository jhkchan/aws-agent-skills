# Eval prompt: appconfig-terminated-deployment-recovery

Diagnose a TERMINATED AppConfig deployment and plan the recovery.
Walk the pre-flight checks and emit the standard VERDICT block.

## Scenario

An operator reports that AppConfig deployment #14 on application
"checkout-service" (id `abc123`), environment "prod"
(id `env-456`) entered State `TERMINATED` after 18 minutes.

## Known facts

- `get-deployment` EventLog shows: "Configuration profile
  prof-789 was deleted during deployment."
- The configuration profile has been re-created (new id
  `prof-789-restored`).
- The latest hosted configuration version is 9.
- No active `DEPLOYING` deployment exists on env-456.
- The deployment strategy "linear-20-percent-30min-bake" is
  intact.

## Symptom

The operator wants to know why the deployment terminated and what
to do next. They ask whether they can resume deployment #14.
