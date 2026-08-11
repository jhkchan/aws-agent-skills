# Eval prompt: appconfig-rollback-alarm-blocks

Plan an AppConfig start-deployment. Walk the pre-flight checks and
emit the standard VERDICT block.

## Scenario

An operator wants to start an AppConfig deployment in `us-east-1`
for application "checkout-service" (id `abc123`), environment
"prod" (id `env-456`), profile "checkout-config" (id `prof-789`),
version 8. Deployment strategy "linear-20-percent-30min-bake"
with rollback alarm
`arn:aws:cloudwatch:us-east-1:111122223333:alarm:checkout-5xx`.

## Known facts

- `cloudwatch describe-alarms` reports `checkout-5xx` is
  currently in `ALARM` state.
- The 5xx error rate is at 3.2% over the last 10 minutes.
- The operator wants to start the deployment anyway.
- The caller holds `appconfig:StartDeployment`.

## Symptom

The operator asks whether it is safe to start the deployment.
