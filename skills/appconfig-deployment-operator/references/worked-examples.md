# Worked Examples — AppConfig Deployment Operator

Secondary worked examples and setup boilerplate moved verbatim from
the SKILL.md body for progressive disclosure (agentskills.io). Loaded
on demand by the skill.

---

### Create application + environment + freeform profile (one-time setup)

```bash
aws appconfig create-application \
  --name "checkout-service" \
  --description "Checkout microservice configuration"

# Capture ApplicationId from the response.
APP_ID=$(aws appconfig list-applications --query 'Items[?Name==`checkout-service`].Id' --output text)

aws appconfig create-environment \
  --application-id $APP_ID \
  --name "prod" \
  --description "Production environment"

ENV_ID=$(aws appconfig list-environments --application-id $APP_ID --query 'Items[?Name==`prod`].Id' --output text)

aws appconfig create-configuration-profile \
  --application-id $APP_ID \
  --name "checkout-config" \
  --location-uri "hosted" \
  --type "AWS.Freeform" \
  --description "Freeform JSON configuration"

PROFILE_ID=$(aws appconfig list-configuration-profiles --application-id $APP_ID --query 'Items[?Name==`checkout-config`].Id' --output text)

# Upload the hosted configuration (<= 64 KB):
aws appconfig create-hosted-configuration-version \
  --application-id $APP_ID \
  --configuration-profile-id $PROFILE_ID \
  --content-type "application/json" \
  --content file://config.json
```

### Worked example — rollback blocked (BLOCKED)

```text
OPERATION: rollback
VERDICT: BLOCKED
TARGET: checkout-service / prod / deployment #14, us-east-1
PRE_CHECKS:
  - [PASS] get-deployment returns deployment #14
  - [FAIL] Deployment State is COMPLETED, not DEPLOYING. StopDeployment / rollback applies only to an active DEPLOYING deployment.
  - [FAIL] No prior COMPLETED deployment exists for environment env-456 (this was the first deployment). Rollback has no known-good version to revert to.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
STATE: COMPLETED (cannot roll back)
PERCENTAGE_COMPLETE: 100.00
NOTES:
  - To revert, issue a new start-deployment referencing the previous configuration version. Capture the prior version via:
    aws appconfig list-hosted-configuration-versions --application-id abc123 --configuration-profile-id prof-789
```
