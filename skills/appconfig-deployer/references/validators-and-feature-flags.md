# Validators and Feature Flags — AppConfig Deployer

Deep reference on Lambda validators (deployment validation lifecycle,
validator function patterns, failure modes), feature flag schema
design, JSON schema validation, and feature flag management via the
AppConfig API. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Lambda validators

### Validator lifecycle

Lambda validators are attached to a configuration profile at creation
time. They run BEFORE every deployment of that profile. A failing
validator blocks the deployment entirely — no targets receive the
configuration.

```text
Deployment with validator:
  1. Operator initiates deployment (start-deployment)
  2. AppConfig invokes the Lambda validator with the new config content
  3. Validator returns 200 (valid) or non-200 (invalid)
     ├── 200 → deployment proceeds (growth steps begin)
     └── non-200 → deployment is BLOCKED (state = ROLLED_BACK)
  4. If blocked, the operator must fix the config and create a new version
```

### Creating a validator function

```python
import json

def lambda_handler(event, context):
    """
    AppConfig Lambda validator.
    event['content'] contains the raw configuration content.
    event['application'] contains the application ID.
    event['environment'] contains the environment ID.
    event['configurationProfile'] contains the profile ID.
    event['versionNumber'] contains the version number.
    """
    try:
        config = json.loads(event['content'])
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Invalid JSON: {str(e)}'})
        }

    # Validate required top-level keys
    required_keys = ['timeout', 'retries', 'feature_flags']
    for key in required_keys:
        if key not in config:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Missing required key: {key}'})
            }

    # Validate value ranges
    if not (1 <= config['timeout'] <= 300):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'timeout must be between 1 and 300'})
        }

    if not (0 <= config['retries'] <= 10):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'retries must be between 0 and 10'})
        }

    # Validate feature flag structure
    for flag_name, flag_config in config['feature_flags'].items():
        if 'enabled' not in flag_config:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Flag {flag_name} missing "enabled" field'
                })
            }
        if not isinstance(flag_config['enabled'], bool):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Flag {flag_name} "enabled" must be boolean'
                })
            }

    return {'statusCode': 200, 'body': json.dumps({'valid': True})}
```

### Attaching a validator to a configuration profile

```bash
VALIDATOR_ARN=$(aws lambda get-function \
  --function-name config-validator \
  --query 'Configuration.FunctionArn' \
  --output text)

aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "validated-config" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --validators "[{\"Type\":\"LAMBDA\",\"Content\":\"${VALIDATOR_ARN}\"}]"
```

### Adding a validator to an existing profile

Validators can be added when creating a profile. To add a validator
to an existing profile, use update-configuration-profile:

```bash
aws appconfig update-configuration-profile \
  --application-id "$APP_ID" \
  --configuration-profile-id "$PROFILE_ID" \
  --validators "[{\"Type\":\"LAMBDA\",\"Content\":\"${VALIDATOR_ARN}\"}]"
```

### Validator failure modes

| Scenario | Validator behavior | Deployment outcome |
|---|---|---|
| Config is valid JSON, passes all checks | Returns 200 | Deployment proceeds |
| Config is invalid JSON (parse error) | Returns 400 with parse error | Deployment blocked |
| Config missing required field | Returns 400 with missing field | Deployment blocked |
| Config value out of range | Returns 400 with range error | Deployment blocked |
| Lambda function fails (exception) | AppConfig treats as validation failure | Deployment blocked |
| Lambda function times out | AppConfig treats as validation failure | Deployment blocked |

**Key:** a validator failure (for any reason) blocks the deployment.
This is by design — it is safer to block a deployment than to deploy
an unvalidated configuration.

## Feature flags

### Feature flag configuration profile

Feature flags use a configuration profile with a specific schema.
The profile type is `AWS.Freeform`, but the content follows the
feature flag schema structure.

**Feature flag schema:**

```json
{
  "flags": {
    "newCheckoutFlow": {
      "enabled": true,
      "percentage": 25
    },
    "betaDashboard": {
      "enabled": false,
      "percentage": 0
    },
    "darkMode": {
      "enabled": true,
      "percentage": 100
    }
  }
}
```

### Creating a feature flag configuration profile

```bash
PROFILE_ID=$(aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "feature-flags" \
  --location-uri "hosted" \
  --type "AWS.Freeform" \
  --query 'Id' --output text)

# Upload initial flag configuration
aws appconfig create-hosted-configuration-version \
  --application-id "$APP_ID" \
  --configuration-profile-id "$PROFILE_ID" \
  --content '{"flags":{"newCheckoutFlow":{"enabled":false,"percentage":0}}}' \
  --content-type "application/json"
```

### Managing feature flags via API

Applications retrieve feature flags via the StartConfigurationSession
and GetLatestConfiguration APIs (or via the AppConfig Lambda/ECS
Agent):

```python
import boto3

appconfig = boto3.client('appconfig')

# Start a configuration session
session = appconfig.start_configuration_session(
    ApplicationIdentifier='my-app-config',
    EnvironmentIdentifier='production',
    ConfigurationProfileIdentifier='feature-flags'
)

# Get the latest configuration
config = appconfig.get_latest_configuration(
    ConfigurationToken=session['InitialConfigurationToken']
)

# Parse the flag values
import json
flags = json.loads(config['Configuration'].read())['flags']
```

### Feature flag vs standard JSON configuration

| Aspect | Feature flag profile | Standard JSON profile |
|---|---|---|
| Profile type | AWS.Freeform with flag schema | AWS.AppConfig.JSON |
| API support | StartConfigurationSession, flag-level operations | GetLatestConfiguration (blob) |
| Schema validation | Flag schema (enabled, percentage) | JSON schema (custom) |
| Dynamic updates | Via deployment (rollout strategy) | Via deployment (rollout strategy) |
| Lambda agent | Supported (flag-level caching) | Supported (blob caching) |

**Key:** feature flags are NOT just JSON configurations. They use a
specific schema that enables the AppConfig feature flag agent and
flag-level API operations. A standard JSON profile without the schema
does NOT support flag-level operations.

## JSON schema validation

### Attaching a JSON schema to a profile

For JSON/YAML profiles, a JSON schema can be attached to validate
structure at version creation time:

```bash
SCHEMA='{"type":"object","properties":{"timeout":{"type":"number","minimum":1,"maximum":300},"retries":{"type":"integer","minimum":0,"maximum":10}},"required":["timeout","retries"]}'

aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "schema-validated" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --validators "[{\"Type\":\"JSON_SCHEMA\",\"Content\":\"${SCHEMA}\"}]"
```

### JSON schema vs Lambda validator

| Validation type | When it runs | What it catches |
|---|---|---|
| JSON schema | At version creation time | Structural errors (type, required, range, pattern) |
| Lambda validator | At deployment time | Semantic errors (business logic, cross-field dependencies) |

Both are complementary. JSON schema catches structural issues early.
Lambda validators catch semantic issues before deployment.

## Terraform examples

```hcl
# Configuration profile with Lambda validator
resource "aws_appconfig_configuration_profile" "validated" {
  application_id = aws_appconfig_application.app.id
  name           = "validated-config"
  location_uri   = "hosted"
  type           = "AWS.AppConfig.JSON"

  validator {
    type    = "LAMBDA"
    content = aws_lambda_function.config_validator.arn
  }

  validator {
    type    = "JSON_SCHEMA"
    content = jsonencode({
      type       = "object"
      properties = {
        timeout = { type = "number", minimum = 1, maximum = 300 }
      }
      required = ["timeout"]
    })
  }
}

# Feature flag configuration profile
resource "aws_appconfig_configuration_profile" "feature_flags" {
  application_id = aws_appconfig_application.app.id
  name           = "feature-flags"
  location_uri   = "hosted"
  type           = "AWS.Freeform"
}

# Hosted configuration version (feature flag content)
resource "aws_appconfig_hosted_configuration_version" "flags_v1" {
  application_id           = aws_appconfig_application.app.id
  configuration_profile_id = aws_appconfig_configuration_profile.feature_flags.id
  content = jsonencode({
    flags = {
      newCheckoutFlow = { enabled = false, percentage = 0 }
    }
  })
  content_type = "application/json"
}
```

---

## Step-by-step CLI walkthroughs (moved verbatim from SKILL.md)

The SKILL.md body keeps only step stubs under progressive disclosure
(agentskills.io); the original step sections below were moved verbatim
so no content is lost.

## Step 6 — Lambda validators (deployment validation)

Lambda validators run BEFORE the deployment begins. They validate the
configuration content and block deployment if validation fails. See
`references/validators-and-feature-flags.md` for a full validator
function example with semantic validation patterns.

**Attach the validator to a configuration profile:**

```bash
aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "validated-config" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --validators '[{"Type":"LAMBDA","Content":"'$(aws lambda get-function --function-name config-validator --query Configuration.FunctionArn --output text)'"}]'
```

**Critical:** validators run on EVERY deployment of that profile. A
failing validator blocks the deployment entirely.

## Step 7 — Feature flags and dynamic JSON schema

Feature flags enable dynamic configuration management. They use a
specific configuration profile schema that supports flag-level
operations.

**Create a feature flag schema:**

```json
{
  "flags": {
    "newCheckoutFlow": {
      "enabled": true,
      "percentage": 25
    },
    "betaDashboard": {
      "enabled": false,
      "percentage": 0
    }
  }
}
```

**JSON schema validation for configuration profiles:**

For JSON/YAML profiles, attach a JSON schema to validate structure:

```bash
aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "schema-validated-config" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --validators '[{"Type":"JSON_SCHEMA","Content":"{\"type\":\"object\",\"properties\":{\"timeout\":{\"type\":\"number\",\"minimum\":1,\"maximum\":300}},\"required\":[\"timeout\"]}"}]'
```

**Key:** JSON schema validation catches structural errors at version
creation time. Lambda validators catch semantic errors at deployment
time. Both are complementary.
