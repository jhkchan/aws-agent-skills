# End-to-End Example: AppConfig Deployment

A walkthrough showing how to use the `appconfig-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an AppConfig application with a linear
deployment strategy, a JSON configuration profile, a Lambda
validator, and CloudWatch alarm-based rollback. The deployment
needs:

- Application: my-app-config (abc12345)
- Environment: production (def67890)
- Configuration profile: app-settings (ghi11111) — JSON
- Deployment strategy: linear, 20% growth, 10-minute bake
- Lambda validator: config-validator
- CloudWatch alarm: appconfig-deploy-error-rate
- Tags: Environment=production, Application=my-app

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-appconfig
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an AppConfig application with a linear deployment
      strategy, 20% growth, 10-minute bake time. Attach a Lambda
      validator and configure a CloudWatch alarm for rollback."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an appconfig deployment"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
APPCONFIG: my-app-config (abc12345) / production (def67890)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Application: my-app-config (abc12345)
  [✓] Environment: production (def67890)
  [✓] Configuration profile: app-settings (ghi11111) — type: AWS.AppConfig.JSON
  [✓] Configuration version: 3
  [✓] Deployment strategy: linear-20pct-10min (jkl22222) — LINEAR growth=20% bake=10min
  [✓] Lambda validator: config-validator (arn:aws:lambda:us-east-1:123456789012:function:config-validator)
  [✓] JSON schema validation: enabled
  [✓] Feature flags: disabled
  [✓] CloudWatch alarms: appconfig-deploy-error-rate (arn:aws:cloudwatch:us-east-1:123456789012:alarm:appconfig-deploy-error-rate) [monitored during bake time]
  [✓] KMS encryption: AWS-managed
  [✓] Rollback on alarm: enabled (auto-rollback during bake time)
  [✓] Tags: Environment=production, Application=my-app
VERIFICATION_COMMANDS:
  aws appconfig get-application --application-id abc12345
  aws appconfig list-environments --application-id abc12345
  aws appconfig get-configuration-profile --application-id abc12345 --configuration-profile-id ghi11111
  aws appconfig get-deployment-strategy --deployment-strategy-id jkl22222
  aws appconfig get-deployment --application-id abc12345 --environment-id def67890 --deployment-number 1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the application
APP_ID=$(aws appconfig create-application \
  --name "my-app-config" \
  --description "Configuration management for my application" \
  --query 'Id' --output text)

# Step 2: Create the environment
ENV_ID=$(aws appconfig create-environment \
  --application-id "$APP_ID" \
  --name "production" \
  --description "Production environment" \
  --query 'Id' --output text)

# Step 3: Create the configuration profile with Lambda validator
PROFILE_ID=$(aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "app-settings" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --validators '[{"Type":"LAMBDA","Content":"arn:aws:lambda:us-east-1:123456789012:function:config-validator"}]' \
  --query 'Id' --output text)

# Step 4: Create the deployment strategy
STRATEGY_ID=$(aws appconfig create-deployment-strategy \
  --name "linear-20pct-10min" \
  --growth-factor 20 \
  --growth-type "LINEAR" \
  --replicate-to "NONE" \
  --final-bake-time-in-minutes 10 \
  --query 'Id' --output text)

# Step 5: Create a configuration version
VERSION_ID=$(aws appconfig create-hosted-configuration-version \
  --application-id "$APP_ID" \
  --configuration-profile-id "$PROFILE_ID" \
  --content '{"timeout": 30, "retries": 3}' \
  --content-type "application/json" \
  --query 'VersionNumber' --output text)

# Step 6: Start the deployment
DEPLOYMENT_ID=$(aws appconfig start-deployment \
  --application-id "$APP_ID" \
  --environment-id "$ENV_ID" \
  --deployment-strategy-id "$STRATEGY_ID" \
  --configuration-profile-id "$PROFILE_ID" \
  --configuration-version "$VERSION_ID" \
  --description "Deploy timeout configuration update" \
  --query 'DeploymentNumber' --output text)
```

---

## Step 4 — Post-deployment verification

```bash
# Check deployment status — should progress through DEPLOYING → BAKING → COMPLETE
aws appconfig get-deployment \
  --application-id "$APP_ID" \
  --environment-id "$ENV_ID" \
  --deployment-number "$DEPLOYMENT_ID"

# Verify the configuration is live
aws appconfig get-configuration \
  --application "$APP_ID" \
  --environment "$ENV_ID" \
  --configuration "$PROFILE_ID" \
  --client-id "verification-client"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Deployment strategy | Missing or all-at-once | Linear/exponential with bake time | Strategy + bake time controls rollout safety; all-at-once = no safety net |
| Lambda validator | Not attached | Validator attached to profile | Validator runs BEFORE deploy, catches bad configs |
| CloudWatch alarms | Not configured | Alarm attached during bake time | Alarms enable auto-rollback during rollout |
| Profile type | Wrong type chosen | Correct type (JSON/YAML/Freeform) | Type is immutable after creation |
| Feature flags | Standard JSON profile | Feature flag schema profile | Flags need specific schema for flag-level API |
| JSON schema | No schema | Schema validates at version creation | Catches structural errors before deployment |

---

## Related artifacts

- **Skill definition:** `skills/appconfig-deployer/SKILL.md`
- **Deployment strategies and alarms guide:** `skills/appconfig-deployer/references/deployment-strategies-and-alarms.md`
- **Validators and feature flags guide:** `skills/appconfig-deployer/references/validators-and-feature-flags.md`
- **Slash command:** `commands/aws/deploy-appconfig.md`
- **Eval suite:** `skills/appconfig-deployer/evals/evals.json`
- **Legacy test cases:** `skills/appconfig-deployer/eval/test-cases.yaml`
