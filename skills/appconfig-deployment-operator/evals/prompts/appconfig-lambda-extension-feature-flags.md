# Eval prompt: appconfig-lambda-extension-feature-flags

Wire the AppConfig Lambda extension for runtime feature flags.
Walk the pre-flight checks and emit the standard VERDICT block.

## Scenario

An operator wants to adopt the AppConfig Lambda extension so a
Lambda function "checkout-handler" in `us-east-1` reads a
feature-flag configuration "checkout-flags" (profile id
`prof-flags-001`, type `AWS.AppConfig.FeatureFlags`) at runtime,
polling every 45 seconds, without redeploying the function on
each flag change.

## Known facts

- **Application:** "checkout-service" (id `abc123`).
- **Environment:** "prod" (id `env-456`).
- **Function's execution role** already holds the required
  AppConfig read permissions and `kms:Decrypt` on the configured
  KMS key.
- **Region:** us-east-1.

## Symptom

The operator needs the exact `update-function-configuration`
command (with the extension layer ARN and required environment
variables) and the function code pattern for reading the flag.
