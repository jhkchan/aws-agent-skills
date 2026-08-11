# Eval: linear-deployment-with-alarms

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — linear deployment strategy, 20% growth, 10-minute bake, Lambda validator, CloudWatch alarm for rollback

## Prompt

Create an AppConfig application named my-app-config in
us-east-1. Environment: production. Configuration profile:
app-settings (JSON). Deployment strategy: linear, 20% growth
factor, 10-minute bake time. Attach a Lambda validator
(config-validator function). Configure a CloudWatch alarm
(appconfig-deploy-error-rate) for rollback during bake time.
Application ID abc12345. Environment ID def67890. Profile ID
ghi11111. Strategy ID jkl22222. Tags: Environment=production.
