# Lambda extension and runtime integration — deep reference

This reference expands the SKILL.md Lambda extension, AppConfig
agent, and runtime integration sections. Load when wiring the
Lambda extension, the EC2 / ECS / EKS agent, or direct
`GetConfiguration` API calls.

## Lambda extension architecture

### How the extension works

1. The Lambda runtime loads the `AWS-AppConfig-Extension` layer
   during the function's init phase.
2. The extension reads the `AWS_APPCONFIG_EXTENSION_*` environment
   variables to identify the application, environment, and
   configuration profile.
3. The extension opens an HTTP server on `localhost:2772`.
4. The extension polls AppConfig on the configured interval
   (45 seconds minimum) and caches the latest configuration.
5. The Lambda function reads the configuration via HTTP GET to
   `localhost:2772/applications/<app>/environments/<env>/configurations/<profile>`.
6. The extension updates the cache in the background; the function
   sees the new configuration on its next invocation (within the
   polling interval).

### Required environment variables

| Variable | Meaning | Required |
|---|---|---|
| `AWS_APPCONFIG_EXTENSION_APPLICATION_NAME` | AppConfig application name | Yes |
| `AWS_APPCONFIG_EXTENSION_ENVIRONMENT` | AppConfig environment name | Yes |
| `AWS_APPCONFIG_EXTENSION_CONFIGURATION_PROFILE` | Configuration profile name | Yes |
| `AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_SECONDS` | Polling interval (45-3600, default 45) | No |
| `AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_MAX_SECONDS` | Max backoff interval | No |
| `AWS_APPCONFIG_EXTENSION_HTTP_PORT` | HTTP port (default 2772) | No |
| `AWS_APPCONFIG_EXTENSION_ROLE_ARN` | Assume-role ARN (cross-account) | No |

Without the required variables, the extension does not preload —
`localhost:2772` returns 404.

### Required IAM permissions

The Lambda function's execution role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "appconfig:GetApplication",
        "appconfig:GetEnvironment",
        "appconfig:GetConfigurationProfile",
        "appconfig:GetConfiguration",
        "appconfig:StartConfigurationSession"
      ],
      "Resource": "arn:aws:appconfig:<region>:<account>:application/<app-id>/environment/<env-id>/configurationprofile/<profile-id>"
    }
  ]
}
```

If the configuration is encrypted with a customer-managed KMS key,
add `kms:Decrypt` on the key.

### Function code pattern (Node.js)

```javascript
const http = require('http');

const APP = process.env.AWS_APPCONFIG_EXTENSION_APPLICATION_NAME;
const ENV = process.env.AWS_APPCONFIG_EXTENSION_ENVIRONMENT;
const PROFILE = process.env.AWS_APPCONFIG_EXTENSION_CONFIGURATION_PROFILE;

function getConfig() {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: 'localhost',
      port: 2772,
      path: `/applications/${APP}/environments/${ENV}/configurations/${PROFILE}`,
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    };
    const req = http.request(opts, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        if (res.statusCode === 200) {
          resolve(JSON.parse(body));
        } else if (res.statusCode === 304) {
          resolve(null);  // No change since last poll
        } else {
          reject(new Error(`AppConfig extension returned ${res.statusCode}`));
        }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

exports.handler = async (event) => {
  const config = await getConfig();
  if (config) {
    // Use the latest configuration — feature flag, dynamic value, etc.
    const timeout = config.flags?.long_timeout?.enabled ? 5000 : 1000;
    // ...
  }
  return { statusCode: 200 };
};
```

The function never calls the AWS SDK directly for AppConfig — the
extension handles polling, caching, and IAM.

### Function code pattern (Python)

```python
import json
import urllib.request
import os

APP = os.environ['AWS_APPCONFIG_EXTENSION_APPLICATION_NAME']
ENV = os.environ['AWS_APPCONFIG_EXTENSION_ENVIRONMENT']
PROFILE = os.environ['AWS_APPCONFIG_EXTENSION_CONFIGURATION_PROFILE']

def get_config():
    url = f'http://localhost:2772/applications/{APP}/environments/{ENV}/configurations/{PROFILE}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                return json.loads(resp.read())
            return None  # 304 = no change
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return None
        raise

def lambda_handler(event, context):
    config = get_config()
    if config:
        timeout = 5000 if config.get('flags', {}).get('long_timeout', {}).get('enabled') else 1000
    return {'statusCode': 200}
```

### Layer ARNs (2026)

The AppConfig extension layer is published by account
`027253079308` in every commercial region:

```
arn:aws:lambda:<region>:027253079308:layer:AWS-AppConfig-Extension:<version>
```

Always use the latest version. The layer is compatible with
`nodejs20.x`, `nodejs22.x`, `python3.11`, `python3.12`,
`java21`, `provided.al2023` runtimes.

## AppConfig agent (EC2 / ECS / EKS)

### Agent architecture

The `aws-appconfig-agent` is a sidecar container (ECS / EKS) or
a systemd service (EC2) that:

1. Reads the application, environment, and configuration profile
   from environment variables or `/etc/aws-appconfig/agent.yaml`.
2. Polls AppConfig every 60 seconds (configurable).
3. Writes the active configuration to a local file
   (`/etc/aws-appconfig/config.json` by default).
4. The application reads the local file (no AWS SDK call needed).

### ECS / EKS sidecar manifest

```yaml
# ECS task definition sidecar:
{
  "name": "appconfig-agent",
  "image": "public.ecr.aws/aws-appconfig/aws-appconfig-agent:2.x",
  "essential": true,
  "environment": [
    {"name": "APPLICATION_NAME", "value": "checkout-service"},
    {"name": "ENVIRONMENT", "value": "prod"},
    {"name": "CONFIGURATION_PROFILE", "value": "checkout-config"},
    {"name": "POLL_INTERVAL", "value": "60"}
  ],
  "mountPoints": [
    {"sourceVolume": "appconfig", "containerPath": "/etc/aws-appconfig"}
  ]
}
```

The application container mounts the same `appconfig` volume and
reads `/etc/aws-appconfig/config.json` (or the agent's configured
output path).

### Agent IAM permissions

The agent's task role / pod role / EC2 instance profile needs the
same `appconfig:Get*` permissions as the Lambda extension's role,
plus `kms:Decrypt` if the configuration is encrypted.

### Polling interval and startup behavior

- Default poll interval: 60 seconds.
- On startup, the agent performs an immediate poll, then polls at
  the configured interval.
- The agent writes the configuration atomically (write to temp
  file, then rename) to avoid partial reads.
- If the agent cannot reach AppConfig (network, IAM), it serves
  the last cached configuration and logs the error.

## Direct GetConfiguration API

### When to call the API directly

- The runtime does not support the Lambda extension (e.g., a
  custom runtime without layer support).
- The application needs sub-45-second polling (advanced use case).
- The application wants explicit control over the polling cadence
  and retry behavior.

### API pattern

```bash
# Start a configuration session:
aws appconfig start-configuration-session \
  --application-identifier <app-id-or-name> \
  --environment-identifier <env-id-or-name> \
  --configuration-profile-identifier <profile-id-or-name> \
  --required-min PollIntervalInSeconds=45

# Returns InitialConfigurationToken. Use it to fetch the configuration:
aws appconfig get-latest-configuration \
  --configuration-session-token <token>  # Returns NextPollConfiguration token for the next call
```

`StartConfigurationSession` + `GetLatestConfiguration` replaces the
older `GetConfiguration` API (still supported but deprecated for
new integrations).

### Polling contract

- The response includes `NextPollConfigurationToken`,
  `NextPollIntervalInSeconds`, and the `Configuration` blob (or
  empty if no change since the last poll).
- Always use the returned `NextPollIntervalInSeconds`; AppConfig
  throttles aggressive pollers.
- The session expires after 24 hours; restart with
  `StartConfigurationSession` if needed.

## Feature flag schema

### AWS.AppConfig.FeatureFlags profile

A feature-flag profile uses a typed schema with a structured
payload:

```json
{
  "version": "1",
  "flags": {
    "new_checkout_flow": {
      "name": "new_checkout_flow",
      "enabled": true
    },
    "long_timeout": {
      "name": "long_timeout",
      "enabled": false
    },
    "experimental_feature": {
      "name": "experimental_feature",
      "enabled": true,
      "attributes": {
        "variant": {
          "type": "string"
        }
      }
    }
  }
}
```

### Validators

The feature-flag profile type requires a Validators entry with
`Type: JSON_SCHEMA` pointing at a feature-flag schema document.
AppConfig validates each hosted configuration version against
the schema at upload time.

### Attribute-level evaluation

The runtime reads `flags.<name>.enabled` for the on/off state,
and `flags.<name>.attributes.<key>` for variant / parameter
values. The Lambda extension returns the full payload; the
application extracts the relevant flag.

## Common runtime integration pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Missing `AWS_APPCONFIG_EXTENSION_*` env vars | `localhost:2772` returns 404 | Set the three required env vars on the Lambda function |
| Lambda role missing `appconfig:StartConfigurationSession` | Extension logs `AccessDenied` on init | Attach the AppConfig read permissions to the role |
| KMS key not decryptable by Lambda role | Extension serves stale cache indefinitely | Add `kms:Decrypt` on the configured KMS key to the role |
| Function reads config at module scope only | New configuration not picked up until cold start | Read config inside the handler (each invocation) |
| Agent on ECS without shared volume | Application container cannot read `/etc/aws-appconfig/config.json` | Mount the volume in both containers |
| Direct API polling too aggressively | `ThrottlingException` from AppConfig | Respect `NextPollIntervalInSeconds`; minimum is 45 seconds |
| Feature-flag payload sent as freeform | Validation error at `create-hosted-configuration-version` | Use `Type: AWS.AppConfig.FeatureFlags` profile with the flag schema |

---

## Step-by-step CLI walkthroughs (moved verbatim from SKILL.md)

The SKILL.md body keeps only pattern stubs under progressive disclosure
(agentskills.io); the original boilerplate sections below were moved
verbatim so no content is lost.

### Lambda extension (runtime feature flags without redeploy)

Add the AppConfig extension layer to the Lambda function, then set
environment variables:

```bash
aws lambda update-function-configuration \
  --function-name checkout-handler \
  --layers arn:aws:lambda:us-east-1:027253079308:layer:AWS-AppConfig-Extension:131 \
  --environment '{
    "Variables": {
      "AWS_APPCONFIG_EXTENSION_APPLICATION_NAME": "checkout-service",
      "AWS_APPCONFIG_EXTENSION_ENVIRONMENT": "prod",
      "AWS_APPCONFIG_EXTENSION_CONFIGURATION_PROFILE": "checkout-config",
      "AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_SECONDS": "45"
    }
  }'
```

The function reads the configuration via HTTP GET to
`http://localhost:2772/applications/checkout-service/environments/prod/configurations/checkout-config`
— no AWS SDK call needed. The extension polls AppConfig every 45
seconds and caches; updates land within the polling interval without
a function redeploy.
