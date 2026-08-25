# Endpoints and Domains — Lightsail Container Deployer

Deep reference on public endpoint configuration (HTTPS, health check
customization, port mapping), managed TLS certificate behavior, custom
domain setup via DNS CNAME, CloudWatch Logs integration, and environment
variable vs secret management. Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays scannable.

## Public endpoint fundamentals

### How the public endpoint works

When you create a deployment with a container port mapped to HTTP,
Lightsail provisions a public endpoint with a managed HTTPS URL:

```text
https://<unique-id>.<region>.cs.amazonlightsail.com

Example:
  https://abc123def456.us-east-1.cs.amazonlightsail.com
```

The endpoint:
- Is HTTPS only (TLS 1.2+).
- Has a managed TLS certificate (auto-provisioned, auto-renewed).
- Routes traffic to the container on the mapped port.
- Performs health checks on the configured path.

### Port mapping

Container ports must be mapped as HTTP. Lightsail does not support TCP
or UDP port mappings on the public endpoint.

```json
{
  "my-app": {
    "image": "my-app:v1.0",
    "ports": {
      "8080": "HTTP"
    }
  }
}
```

The public endpoint's `containerPort` must match one of the mapped ports.

### Health check configuration

| Parameter | Default | Range | Notes |
|---|---|---|---|
| Path | / | Any path | Must return HTTP 200 |
| Success codes | 200 | 200-299 | HTTP status codes for healthy |
| Interval | 5s | 5-300s | Time between checks |
| Healthy threshold | 2 | 1-10 | Consecutive successes to mark healthy |
| Unhealthy threshold | 2 | 1-10 | Consecutive failures to mark unhealthy |

```json
{
  "containerName": "my-app",
  "containerPort": 8080,
  "healthCheck": {
    "healthyThreshold": 2,
    "unhealthyThreshold": 2,
    "intervalSeconds": 5,
    "path": "/health",
    "successCodes": "200"
  }
}
```

### Health check best practices

- Use a dedicated health endpoint (e.g., `/health`) rather than `/`.
- The endpoint should check database connectivity and critical
  dependencies.
- Return HTTP 200 for healthy, HTTP 503 for unhealthy.
- Do not redirect (3xx) on the health endpoint.

## Managed TLS certificate

### Auto-provisioned at endpoint creation

Lightsail automatically provisions a TLS certificate when the public
endpoint is created. The certificate:

- Covers the default domain (`*.cs.amazonlightsail.com`).
- Is managed by Lightsail (no ACM integration needed).
- Is auto-renewed before expiry.
- Supports TLS 1.2 and 1.3.

No manual certificate upload, ACM validation, or renewal management is
required.

### Extending TLS to custom domains

When a custom domain CNAME is configured and resolves to the service's
public endpoint, Lightsail automatically extends the managed TLS
certificate to cover the custom domain.

```text
Default domain:  abc123.us-east-1.cs.amazonlightsail.com  → TLS ✓
Custom domain:   app.example.com (CNAME → default)        → TLS ✓ (auto-extended)
```

## Custom domain setup

### Step 1: Get the public endpoint domain

```bash
PUBLIC_DOMAIN=$(aws lightsail get-container-services \
  --service-name "my-app" \
  --query 'containerServices[0].currentDeployment.publicEndpoint.containerName' \
  --output text)
```

### Step 2: Add CNAME record

**Route 53:**

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1DEXAMPLE \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "abc123.us-east-1.cs.amazonlightsail.com"}]
      }
    }]
  }'
```

**External DNS (e.g., GoDaddy, Cloudflare):**

Add a CNAME record:
- Name: `app` (or `app.example.com`)
- Value: `abc123.us-east-1.cs.amazonlightsail.com`

### Step 3: Verify TLS extension

After the CNAME resolves (usually within minutes), Lightsail detects the
custom domain and extends the TLS certificate. Verify with:

```bash
curl -vI https://app.example.com 2>&1 | grep -E "subject:|issuer:"
```

## Environment variables and secrets

### Environment variables (plaintext)

Environment variables are stored in plaintext in the deployment
configuration. They are visible in `get-container-services` API
responses.

```json
{
  "my-app": {
    "image": "my-app:v1.0",
    "environment": {
      "DATABASE_URL": "postgres://prod-db:5432/myapp",
      "LOG_LEVEL": "info",
      "MAX_CONNECTIONS": "100"
    }
  }
}
```

### Secrets (hidden after creation)

Secrets are passed as environment variables but are NOT returned in
`get-container-services` responses after the deployment is created.
This provides a layer of protection for sensitive values.

```json
{
  "my-app": {
    "image": "my-app:v1.0",
    "environment": {
      "API_KEY": "super-secret-key",
      "JWT_SECRET": "another-secret"
    }
  }
}
```

After deployment, these values are stored securely and not surfaced in
describe calls. However, they are visible in the deployment JSON file
and in the CLI command that created the deployment.

**Best practice:** Use AWS Secrets Manager or Parameter Store for
highly sensitive secrets, and reference them in the container's
startup script. Lightsail's built-in secret handling is suitable for
moderately sensitive values but should not be the sole security
boundary for critical secrets.

## CloudWatch Logs integration

### Enabling container logs

Lightsail Container Service sends container stdout/stderr to
CloudWatch Logs automatically when the service is configured for
logging.

```bash
# View container service deployments (includes log configuration)
aws lightsail get-container-service-deployments \
  --service-name "my-app"
```

### Viewing logs

```bash
aws logs get-log-events \
  --log-group-name "/aws/lightsail/container/my-app" \
  --log-stream-name "my-app/latest" \
  --limit 50
```

### Log structure

Each log entry includes:
- Timestamp
- Container name
- Deployment version
- stdout/stderr message

This makes it easy to correlate log entries with specific deployments
and track application behavior across redeployments.

## Expert heuristic: managed TLS vs custom domain (moved from SKILL.md)

Lightsail automatically provisions a managed TLS certificate for the
service's default domain. No manual cert upload or ACM integration is
needed. For custom domains, add a CNAME record.

```text
Default domain (managed TLS auto-provisioned):
  https://<unique-id>.<region>.cs.amazonlightsail.com
  → TLS certificate auto-managed by Lightsail
  → HTTPS works immediately after endpoint is active

Custom domain (CNAME to default domain):
  1. Get the service's public endpoint domain
  2. Add DNS CNAME: app.example.com → <unique>.<region>.cs.amazonlightsail.com
  3. Lightsail validates the CNAME and extends TLS to the custom domain
  4. HTTPS works on app.example.com
```

**Key implication:** managed TLS means no certificate management
overhead. The custom domain process is a simple CNAME, not a cert
upload or ACM validation.

## Step 5 — environment variables template (moved from SKILL.md)

**Environment variables (in containers.json):**

```json
{
  "my-app": {
    "image": "my-app:v1.0",
    "environment": {
      "DATABASE_URL": "postgres://...",
      "LOG_LEVEL": "info",
      "API_KEY": "secret-value"
    },
    "ports": {
      "8080": "HTTP"
    }
  }
}
```

## Step 8 — custom domain commands (moved from SKILL.md)

**Get the public endpoint domain:**

```bash
PUBLIC_DOMAIN=$(aws lightsail get-container-services \
  --service-name "my-app" \
  --query 'containerServices[0].publicEndpoint.url' --output text)

echo "Public endpoint: $PUBLIC_DOMAIN"
```

**Add CNAME record (Route 53 or external DNS):**

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1DEXAMPLE \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'"$PUBLIC_DOMAIN"'"}]
      }
    }]
  }'
```

## Step 9 — CloudWatch Logs commands (moved from SKILL.md)

```bash
# Enable CloudWatch Logs in the deployment
# Logs are automatically sent to the Lightsail log group
aws lightsail get-container-log \
  --service-name "my-app" \
  --container-name "my-app"
```

**View container logs:**

```bash
aws logs get-log-events \
  --log-group-name "/aws/lightsail/container/my-app" \
  --log-stream-name "my-app/latest"
```

## Step 4 — verify public endpoint command (moved from SKILL.md)

**Verify public endpoint:**

```bash
aws lightsail get-container-services \
  --service-name "my-app" \
  --query 'containerServices[0].publicEndpoint.{Url:containerName,Health:healthCheck}'
```

## Step 2 — endpoint.json template (moved from SKILL.md)

**endpoint.json (public endpoint configuration):**

```json
{
  "containerName": "my-app",
  "containerPort": 80,
  "healthCheck": {
    "healthyThreshold": 2,
    "unhealthyThreshold": 2,
    "intervalSeconds": 5,
    "path": "/",
    "successCodes": "200"
  }
}
```
