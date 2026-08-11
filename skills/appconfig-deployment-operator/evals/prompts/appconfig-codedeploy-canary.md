# Eval prompt: appconfig-codedeploy-canary

Configure a CodeDeploy deployment group using the AppConfig canary
router. Walk the pre-flight checks and emit the standard VERDICT
block.

## Scenario

An operator wants to use CodeDeploy to orchestrate an AppConfig
deployment in `us-east-1`, using the `AppConfig.50Percent`
deployment config (2-step canary).

## Known facts

- **AppConfig application:** "payments-service" (id `pay-abc`).
- **AppConfig environment:** "prod" (id `env-pay`).
- **CodeDeploy application:** "payments-codedeploy" exists.
- **Service role:**
  `arn:aws:iam::111122223333:role/codedeploy-role` has the
  required `appconfig:*` and `codedeploy:*` permissions.
- **Region:** us-east-1.

## Symptom

The operator wants the `create-deployment-group` command and
confirmation that `deploymentStyle.deploymentOption` is
`WITH_TRAFFIC_CONTROL`.
