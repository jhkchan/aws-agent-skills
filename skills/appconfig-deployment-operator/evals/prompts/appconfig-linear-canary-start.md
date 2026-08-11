# Eval prompt: appconfig-linear-canary-start

Start an AppConfig deployment. Walk the pre-flight checks and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, STATE, PERCENTAGE_COMPLETE,
NOTES, CONFIRM).

## Scenario

An operator wants to start an AppConfig deployment
"checkout-timeout-2026-08" in `us-east-1` for application
"checkout-service" (id `abc123`), environment "prod"
(id `env-456`), configuration profile "checkout-config"
(id `prof-789`, type `AWS.Freeform`), configuration version 7.

## Known facts

- **Payload:** raises the checkout timeout from 1000 ms to 5000 ms.
- **Deployment strategy:** custom
  "linear-20-percent-30min-bake" (GrowthFactor 20,
  DeploymentDurationInMinutes 30, BakeTimeInMinutes 30,
  FinalBakeTimeInMinutes 30).
- **Rollback alarm:**
  `arn:aws:cloudwatch:us-east-1:111122223333:alarm:checkout-5xx`
  (currently OK).
- **Caller permissions:** `appconfig:StartDeployment`,
  `appconfig:GetDeployment`.
- **No active DEPLOYING deployment** exists on env-456.
- **KMS key** `arn:aws:kms:us-east-1:111122223333:key/abc` is
  decryptable by the caller.

## Symptom

The operator needs the exact CLI sequence to start the deployment
and the expected wall-clock duration.
