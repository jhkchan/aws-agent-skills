---
name: lightsail-container-deployer
description: >-
  Provisions Amazon Lightsail Container Services with production
  defaults: container service creation (power scale nano/micro/small/
  medium/large/xlarge), deployment (container image from ECR or public
  registry), public endpoint (HTTPS domain, health check path), ECR
  private registry auth (access key and secret), environment variables,
  secrets via Lightsail container parameters, scale (number of nodes),
  container port mapping, managed TLS certificate, custom domain via
  DNS CNAME, CloudWatch Logs integration, and cost predictability
  (all-inclusive pricing). Emits a READY_TO_DEPLOY checklist with
  verification commands. Use when creating a Lightsail container
  service, deploying a container, configuring ECR private auth, setting
  up a public endpoint, or managing scale. Triggers: create lightsail
  container, deploy container service, lightsail power scale, lightsail
  ECR auth, container public endpoint, lightsail environment variables,
  lightsail secrets, lightsail custom domain, lightsail managed TLS.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with lightsail access
  (and ECR access if pulling from a private registry). Works with
  Terraform aws_lightsail_container_service /
  aws_lightsail_container_deployment_version resources and CloudFormation
  via AWS::Lightsail::Container templates (where supported).
keywords:
  - aws
  - lightsail
  - container service
  - cloudops
  - deploy
  - provisioning
  - power scale
  - ecr auth
  - managed tls
  - public endpoint
  - container deployment
  - cost predictable
tags:
  - aws
  - lightsail
  - container
  - cloudops
  - deploy
  - compute
  - provisioning
  - ecr
  - managed-tls
  - public-endpoint
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - lightsail
    - container
    - cloudops
    - deploy
    - compute
    - provisioning
    - ecr
    - managed-tls
    - public-endpoint
  dependencies:
    - aws-orchestrator
  keywords:
    - create lightsail container
    - deploy container service
    - lightsail power scale
    - lightsail ecr auth
    - container public endpoint
    - lightsail environment variables
    - lightsail secrets
    - lightsail custom domain
    - lightsail managed tls
  when_to_use: >-
    Invoke when the user wants to create an Amazon Lightsail Container
    Service, deploy a container image (from ECR or public registry),
    configure ECR private registry auth, set up a public endpoint with
    managed TLS, configure environment variables and secrets, manage
    scale (node count), map container ports, or set up a custom domain.
    Do NOT invoke for ECS/EKS (use ECS/EKS skills), App Runner (use
    App Runner skills), Lambda (use Lambda skills), or Elastic Beanstalk
    (use Beanstalk skills).
---

# Lightsail Container Deployer

An AWS CloudOps agent skill that provisions Amazon Lightsail Container
Services with correct defaults. The skill walks the operator through
container service creation (power scale selection), deployment
(container image from ECR or public registry with auth), public
endpoint (HTTPS domain with managed TLS), environment variables and
secrets, scale (node count), container port mapping, ECR private
registry authentication, managed TLS certificate, custom domain via
DNS CNAME, CloudWatch Logs integration, and cost predictability,
captures power and scale decisions, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create lightsail container, deploy container service, lightsail power
scale, lightsail ECR auth, container public endpoint, lightsail
environment variables, lightsail secrets, lightsail custom domain,
lightsail managed TLS.

## STRICT output contract

When this skill is invoked with a Lightsail-container-provisioning
request (create a container service, deploy a container image,
configure ECR auth, set up a public endpoint, configure environment
variables or secrets, manage scale, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`LIGHTSAIL_CONTAINER:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Container service creation (power scale) | Core service model |
| Step 2 — Container deployment (image, ports) | Image configuration |
| Step 3 — ECR private registry auth | Private image pulls |
| Step 4 — Public endpoint (HTTPS, health check) | Endpoint configuration |
| Step 5 — Environment variables and secrets | App configuration |
| Step 6 — Scale (node count) | Horizontal scaling |
| Step 7 — Managed TLS certificate | HTTPS termination |
| Step 8 — Custom domain via DNS | Custom domain setup |
| Step 9 — CloudWatch Logs integration | Observability |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/power-and-ecr-auth.md | Power scale + ECR detail |
| references/endpoints-and-domains.md | Endpoint + domain detail |

## Mindset

**One-line takeaway:** Lightsail Container Service is a simplified
container hosting platform with all-inclusive pricing. You choose a
power scale (nano through xlarge) and a node count. The service
provides a managed HTTPS endpoint with a TLS certificate. For ECR
private images, you need to provide registry credentials (access key
and secret). Cost is predictable: the monthly price includes compute,
storage, and data transfer.

Three misconceptions dominate Lightsail Container misdesign at
provisioning time:

- **"Power scale and node count are the same thing."** They are not.
  Power scale (nano/micro/small/medium/large/xlarge) determines the
  CPU and RAM per node. Node count (1-20) determines how many replicas
  run. Scaling vertically means increasing power; scaling horizontally
  means increasing nodes. A medium with 2 nodes is different from a
  large with 1 node even if the total cost is similar.

- **"ECR private images work without authentication."** They do not.
  Lightsail Container Service cannot pull from ECR without explicit
  registry credentials. You must create an IAM access key with ECR
  read permissions and pass the access key ID and secret to the
  deployment. Public registry images (Docker Hub) do not need auth.

- **"The managed TLS certificate requires manual configuration."** It
  does not. Lightsail automatically provisions and manages a TLS
  certificate for the service's default domain
  (`<unique>.<region>.cs.amazonlightsail.com`). For custom domains,
  you add a CNAME record pointing to the service's public endpoint.

## Configuration dependency graph (novel heuristic)

Lightsail Container configurations are NOT independent. The container
service must exist before deploying. ECR auth must be configured before
pulling private images. The public endpoint requires a deployment to be
active. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Container service | None | Power scale determines per-node CPU/RAM; can be changed later (requires redeploy) | deployment |
| Deployment (container image) | Container service exists | Image must be accessible; public images work without auth; ECR images need credentials | running containers |
| ECR private registry auth | IAM access key with ECR read permission | Credentials stored in deployment; must be updated if key rotated | private image pulls |
| Public endpoint | At least one container with a port mapped | Endpoint is HTTPS only; managed TLS auto-provisioned | public access |
| Health check | Public endpoint enabled; path must return 200 | Default path is /; unhealthy endpoint blocks deployment success | deployment verification |
| Environment variables | Container service exists | Variables are plaintext in the deployment config | app configuration |
| Secrets | Container service exists | Secrets use Lightsail parameters; not visible in describe calls after creation | sensitive app config |
| Scale (node count) | Container service exists | Scale 1-20; changing scale triggers rolling redeploy | horizontal capacity |
| Managed TLS | Public endpoint enabled | Auto-managed; no manual cert upload needed for default domain | HTTPS termination |
| Custom domain | Public endpoint active; DNS CNAME configured | CNAME must point to the service's public endpoint domain | branded URL |
| CloudWatch Logs | Container service exists; log driver configured | Logs are available in CloudWatch Logs if enabled | observability |

**The power-scale-vs-node-count row is the one a baseline model
misses.** A baseline model treats scaling as a single dimension.
Lightsail separates vertical scaling (power: CPU/RAM per node) from
horizontal scaling (node count: number of replicas). The trade-off
matters: a large with 1 node has no redundancy, while a medium with 2
nodes provides failover at similar cost.

**Cross-dependency gotchas:**
- ECR auth credentials are per-deployment, not per-service. If you
  rotate the IAM key, you must create a new deployment version.
- The public endpoint is only active when a deployment is running with
  a port mapped. If the deployment fails, the endpoint returns 503.
- Health check path must return HTTP 200. A path returning 3xx or 4xx
  marks the endpoint as unhealthy.
- Changing power scale or node count triggers a rolling redeploy.
  Existing containers are replaced.

## Expert heuristic: power scale vs node count trade-off

A baseline model says "pick a size and go." The correct heuristic
recognizes that power scale and node count serve different purposes:

```text
Power scale (per-node capacity):
  ├── nano:    0.25 vCPU, 0.5 GB RAM  — dev/testing
  ├── micro:   0.5 vCPU,  1 GB RAM    — low-traffic
  ├── small:   1 vCPU,    2 GB RAM    — small production
  ├── medium:  2 vCPU,    4 GB RAM    — medium production
  ├── large:   4 vCPU,    8 GB RAM    — high-traffic
  └── xlarge:  8 vCPU,   16 GB RAM    — compute-intensive

Node count (horizontal replicas):
  ├── 1 node  — no redundancy (single point of failure)
  ├── 2 nodes — minimum for high availability
  └── 3+ nodes — production-grade redundancy

Cost comparison (approximate monthly):
  large x 1  ≈ medium x 2  ≈ small x 4
  (similar total cost, but HA requires >= 2 nodes)
```

**Key implication:** for production, always use at least 2 nodes for
redundancy. A medium with 2 nodes provides failover; a large with 1
node does not. The cost is similar, but the availability is very
different.

## Expert heuristic: ECR private auth via access key

Lightsail Container Service cannot pull from ECR without explicit
credentials. You must create an IAM user or role with an access key
that has `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, and
`ecr:GetAuthorizationToken` permissions.

```text
ECR auth flow:
  1. Create IAM user (or use existing) with ECR read permissions
  2. Generate access key (access key ID + secret access key)
  3. Pass credentials to Lightsail deployment:
     aws lightsail create-container-service-deployment
       --service-name my-service
       --containers file://containers.json
       --public-endpoint file://endpoint.json
  4. In containers.json, specify image as:
     <account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>
  5. Lightsail stores the credentials in the deployment

Note: credentials are per-deployment. Rotating the IAM key
requires a new deployment version.
```

**Key implication:** for ECR private images, the access key must be
valid for the lifetime of the deployment. If the key is deactivated or
deleted, the next deployment pull will fail.

## Expert heuristic: managed TLS vs custom domain

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

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Container image available | Image must be in ECR or a public registry | `aws ecr describe-images` or `docker pull` |
| ECR registry credentials (if private) | Lightsail needs access key for private pulls | `aws iam list-access-keys` |
| Power scale decided | Determines CPU/RAM per node | Assess workload requirements |
| Node count decided | Determines horizontal capacity and redundancy | Assess HA requirements |
| Container port identified | Port must be mapped for public endpoint | Confirm application listening port |
| Health check path decided | Path must return HTTP 200 | Confirm health endpoint |
| Environment variables identified | App configuration | List all required variables |
| Secrets identified | Sensitive app configuration | List all secrets (stored as parameters) |
| AWS region selected | Container service is regional | Confirm region |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Container service creation (power scale)

The container service is the top-level resource. Power scale determines
CPU and RAM per node.

| Power | vCPU | RAM | Use case | Approx. monthly cost |
|---|---|---|---|---|
| nano | 0.25 | 0.5 GB | Dev/testing | $7 |
| micro | 0.5 | 1 GB | Low-traffic | $15 |
| small | 1 | 2 GB | Small production | $30 |
| medium | 2 | 4 GB | Medium production | $60 |
| large | 4 | 8 GB | High-traffic | $115 |
| xlarge | 8 | 16 GB | Compute-intensive | $225 |

**Create a container service:**

```bash
aws lightsail create-container-service \
  --service-name "my-app" \
  --power small \
  --scale 2 \
  --tags key=Environment,value=production

echo "Service created: my-app (power: small, scale: 2)"
```

**Verify service status:**

```bash
aws lightsail get-container-services \
  --service-name "my-app" \
  --query 'containerServices[0].{State:State,Power:Power,Scale:Scale}'
```

Wait for state to become `READY` before deploying.

## Step 2 — Container deployment (image, ports)

The deployment defines the container image, port mappings, and
environment variables. Create a deployment JSON file.

**containers.json (public registry image):**

```json
{
  "my-app": {
    "image": "nginx:latest",
    "command": [],
    "environment": {
      "ENV": "production"
    },
    "ports": {
      "80": "HTTP"
    }
  }
}
```

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

**Create the deployment:**

```bash
aws lightsail create-container-service-deployment \
  --service-name "my-app" \
  --containers file://containers.json \
  --public-endpoint file://endpoint.json
```

## Step 3 — ECR private registry auth

For ECR private images, pass registry credentials in the deployment.
Create an IAM access key with ECR read permissions.

**IAM policy for ECR read access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    }
  ]
}
```

**containers.json with ECR image and credentials:**

```json
{
  "my-app": {
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app:v1.0",
    "command": [],
    "environment": {
      "ENV": "production"
    },
    "ports": {
      "8080": "HTTP"
    }
  }
}
```

**Deploy with ECR credentials:**

```bash
aws lightsail create-container-service-deployment \
  --service-name "my-app" \
  --containers file://containers.json \
  --public-endpoint file://endpoint.json
```

**Critical:** ECR credentials are registered at the service level, not
per-deployment. Use `register-container-image` or pass them when
creating the service. If the IAM key is rotated, re-register the
credentials.

## Step 4 — Public endpoint (HTTPS, health check)

The public endpoint provides HTTPS access with a managed TLS
certificate. The endpoint requires a deployment with a mapped port.

| Property | Value | Notes |
|---|---|---|
| Container name | Container from deployment | Must match deployment |
| Container port | Port mapped in deployment | Must be HTTP (not TCP) |
| Health check path | URL path | Must return HTTP 200 |
| Health check interval | 5-300 seconds | Default 5 |
| Healthy threshold | Consecutive successes | Default 2 |
| Unhealthy threshold | Consecutive failures | Default 2 |

**Verify public endpoint:**

```bash
aws lightsail get-container-services \
  --service-name "my-app" \
  --query 'containerServices[0].publicEndpoint.{Url:containerName,Health:healthCheck}'
```

The endpoint URL is:
`https://<unique-id>.<region>.cs.amazonlightsail.com`

## Step 5 — Environment variables and secrets

Environment variables are plaintext in the deployment configuration.
Secrets use Lightsail's parameter system and are not visible after
creation.

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

**Secrets (stored as parameters):**

Secrets are passed as environment variables but are not returned in
`get-container-services` responses after deployment. This provides a
layer of protection compared to plaintext environment variables.

## Step 6 — Scale (node count)

Scale determines the number of container replicas. Changing scale
triggers a rolling redeploy.

```bash
# Scale up to 3 nodes
aws lightsail update-container-service \
  --service-name "my-app" \
  --scale 3
```

**Scaling guidelines:**

| Scale | Recommendation |
|---|---|
| 1 | Development only — no redundancy |
| 2 | Minimum for production — failover capable |
| 3+ | Production-grade — handles node failures |
| Max 20 | Soft limit per service |

**Critical:** changing power scale also triggers a rolling redeploy.
Plan for brief downtime during scale or power changes.

## Step 7 — Managed TLS certificate

Lightsail automatically provisions and manages a TLS certificate for
the service's default domain. No manual ACM integration is needed.

```text
Default domain: https://<unique>.<region>.cs.amazonlightsail.com
TLS: Auto-managed (provisioned, renewed, and rotated by Lightsail)
HTTPS: Works immediately after endpoint is active
```

The TLS certificate covers both the default domain and any custom
domains that have been validated via CNAME.

## Step 8 — Custom domain via DNS

To use a custom domain, add a CNAME record pointing to the service's
public endpoint domain.

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

Once the CNAME resolves, Lightsail extends the managed TLS certificate
to cover the custom domain.

## Step 9 — CloudWatch Logs integration

Lightsail Container Service can send container logs to CloudWatch Logs.
Logs include stdout/stderr from the container.

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

## Step 10 — Recent features

- **Container service power scale expansion (2023-2024):** Added
  xlarge power (8 vCPU, 16 GB RAM) for compute-intensive workloads,
  bringing Lightsail containers closer to ECS-grade capacity.

- **Private container registry auth improvements (2023-2024):**
  Enhanced ECR auth with support for cross-account ECR pulls and
  IAM role-based credential refresh.

- **Custom domain auto-validation (2023-2024):** Lightsail now
  automatically detects CNAME records and extends TLS coverage without
  manual verification steps.

- **Deployment version history (2024-2025):** Container service now
  retains up to 10 deployment versions for rollback. Previous versions
  can be reactivated without recreating the deployment.

- **Environment variable secrets management (2024-2025):** Secrets are
  now stored using Lightsail's parameter system, providing better
  isolation than plaintext environment variables.

- **CloudWatch Logs enhancement (2024-2025):** Container logs now
  include deployment version metadata, making it easier to correlate
  log entries with specific deployments.

- **VPC peering for Lightsail containers (2025-2026):** Lightsail
  Container Services can now peer with VPC resources, enabling direct
  access to RDS databases and other VPC-internal services without
  public endpoints.

## NEVER do these things

1. **NEVER confuse power scale with node count.** Power scale
   (nano-xlarge) is CPU/RAM per node. Node count (1-20) is replicas.
   A large x 1 has no redundancy; a medium x 2 does.

2. **NEVER assume ECR private images work without credentials.**
   Lightsail needs an IAM access key with ECR read permissions. Public
   registry images (Docker Hub) do not need auth.

3. **NEVER deploy with scale 1 in production.** A single node is a
   single point of failure. Use at least 2 nodes for availability.

4. **NEVER assume the public endpoint works without a mapped port.**
   The endpoint requires a container with a port mapped as HTTP. If no
   port is mapped, the endpoint returns 503.

5. **NEVER use plaintext environment variables for secrets.** Use
   Lightsail parameters for secrets. Plaintext variables are visible
   in the deployment configuration.

6. **NEVER forget that changing power or scale triggers a redeploy.**
   Both operations replace existing containers. Plan for brief
   downtime or use rolling deployments.

7. **NEVER assume managed TLS requires manual configuration.** Lightsail
   auto-provisions TLS for the default domain. Custom domains need only
   a CNAME record.

8. **NEVER use Lightsail Container Service for complex orchestration.**
   Lightsail is a simplified platform. For multi-container workloads,
   service mesh, or advanced scheduling, use ECS or EKS.

9. **NEVER ignore the health check path.** The path must return HTTP
   200. A path returning 3xx, 4xx, or 5xx marks the endpoint unhealthy
   and blocks deployment success.

10. **NEVER forget that ECR credentials need rotation awareness.** If
    the IAM access key is deactivated or deleted, the next deployment
    pull will fail. Plan for key rotation.

## Output format (STRICT output contract)

When this skill is invoked, the agent MUST respond with the block defined
below using the literal all-caps labels `LIGHTSAIL_CONTAINER:`,
`VERDICT:`, `CHECKLIST:`, `VERIFICATION_COMMANDS:`, `FORBIDDEN:`, and
`DECISION_TREE:`. Do NOT preface with prose, headings, or disclaimers.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation (marked `[✗]`), and `READY_TO_DEPLOY`
MUST NOT also appear.

### Literal output labels

```text
LIGHTSAIL_CONTAINER: <service-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Power scale: <nano|micro|small|medium|large|xlarge> (<vCPU>, <RAM>)
  [✓|✗] Node count: <N> nodes — <redundancy note>
  [✓|✗] Container image: <uri> — <public | ECR private>
  [✓|✗] ECR auth: <access key configured | Not needed>
  [✓|✗] Container port: <port> → HTTP
  [✓|✗] Public endpoint: <url> — HTTPS, managed TLS
  [✓|✗] Health check: <path> — interval <n>s, threshold <n>
  [✓|✗] Environment variables: <count>
  [✓|✗] Secrets: <count> parameters
  [✓|✗] Managed TLS: auto-provisioned for default domain
  [✓|✗] Custom domain: <domain CNAME | Not configured>
  [✓|✗] CloudWatch Logs: <enabled | disabled>
  [✓|✗] Tags: <key=value>
VERIFICATION_COMMANDS:
  aws lightsail get-container-services --service-name <name>
  aws lightsail get-container-service-deployments --service-name <name>
```

### FORBIDDEN — NEVER do these

1. NEVER confuse power scale with node count. Power scale
   (nano/micro/small/medium/large/xlarge) is CPU and RAM per node. Node
   count (1-20) is replicas. A large x 1 has zero redundancy; a medium x
   2 provides failover at similar cost.

2. NEVER assume ECR private images work without credentials. Lightsail
   needs an IAM access key with `ecr:GetDownloadUrlForLayer`,
   `ecr:BatchGetImage`, and `ecr:GetAuthorizationToken`. Public registry
   images (Docker Hub) do not need auth.

3. NEVER deploy with scale 1 in production. A single node is a single
   point of failure. Use at least 2 nodes for availability.

4. NEVER assume the public endpoint works without a mapped port. The
   endpoint requires a container with a port mapped as HTTP. If no port
   is mapped, the endpoint returns 503.

5. NEVER use plaintext environment variables for secrets. Use Lightsail
   parameters. Plaintext variables are visible in the deployment
   configuration and returned by `get-container-services`.

6. NEVER forget that changing power or scale triggers a rolling redeploy.
   Both operations replace existing containers. Plan for brief downtime
   or ensure health checks pass before traffic shifts.

7. NEVER ignore the health check path. The path must return HTTP 200. A
   path returning 3xx, 4xx, or 5xx marks the endpoint unhealthy and
   blocks deployment success silently.

### Worked example — small container service with ECR private image + managed TLS

Scenario: production API gateway deployed as a Lightsail Container Service
using a private ECR image, 2 nodes for high availability, managed TLS for
HTTPS, and a custom domain via CNAME.

```text
LIGHTSAIL_CONTAINER: api-gateway
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Power scale: small (1 vCPU, 2 GB RAM)
  [✓] Node count: 2 nodes — production redundancy (failover capable)
  [✓] Container image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/api-gateway:v1.2 — ECR private
  [✓] ECR auth: access key AKIARXAMPLEKEY configured (IAM user lightsail-ecr-puller)
  [✓] Container port: 8080 → HTTP
  [✓] Public endpoint: https://qtc4n3q8t.us-east-1.cs.amazonlightsail.com — HTTPS, managed TLS
  [✓] Health check: /health — interval 5s, healthyThreshold 2, unhealthyThreshold 2
  [✓] Environment variables: 3 (NODE_ENV=production, LOG_LEVEL=info, PORT=8080)
  [✓] Secrets: 2 parameters (DATABASE_URL, JWT_SECRET)
  [✓] Managed TLS: auto-provisioned for default domain (qtc4n3q8t.us-east-1.cs.amazonlightsail.com)
  [✓] Custom domain: api.example.com (CNAME → qtc4n3q8t.us-east-1.cs.amazonlightsail.com)
  [✓] CloudWatch Logs: enabled (/aws/lightsail/container/api-gateway)
  [✓] Tags: Environment=production, Project=api-gateway, Team=platform
VERIFICATION_COMMANDS:
  aws lightsail get-container-services --service-name api-gateway
  aws lightsail get-container-service-deployments --service-name api-gateway
```

Deploy commands:

```bash
# 1. Create the container service (small power, 2 nodes for HA)
aws lightsail create-container-service \
  --service-name api-gateway \
  --power small \
  --scale 2 \
  --tags key=Environment,value=production key=Project,value=api-gateway

# 2. Create containers.json with ECR private image + env vars + port
cat > /tmp/containers.json << 'CJSON'
{
  "api-gateway": {
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/api-gateway:v1.2",
    "environment": {
      "NODE_ENV": "production",
      "LOG_LEVEL": "info",
      "PORT": "8080"
    },
    "ports": {
      "8080": "HTTP"
    }
  }
}
CJSON

# 3. Create endpoint.json with health check
cat > /tmp/endpoint.json << 'EJSON'
{
  "containerName": "api-gateway",
  "containerPort": 8080,
  "healthCheck": {
    "healthyThreshold": 2,
    "unhealthyThreshold": 2,
    "intervalSeconds": 5,
    "path": "/health",
    "successCodes": "200"
  }
}
EJSON

# 4. Deploy with ECR credentials
aws lightsail create-container-service-deployment \
  --service-name api-gateway \
  --containers file:///tmp/containers.json \
  --public-endpoint file:///tmp/endpoint.json

# 5. Verify the public endpoint
aws lightsail get-container-services \
  --service-name api-gateway \
  --query 'containerServices[0].{State:State,Power:Power,Scale:Scale,Url:publicEndpoint.url}'

# 6. Add custom domain CNAME in Route 53
PUBLIC_DOMAIN=$(aws lightsail get-container-services \
  --service-name api-gateway \
  --query 'containerServices[0].publicEndpoint.url' --output text)

aws route53 change-resource-record-sets \
  --hosted-zone-id Z2DEXAMPLEZONE \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'"$PUBLIC_DOMAIN"'"}]
      }
    }]
  }'
```

### Decision tree

```text
What power scale is needed?
├─ Dev / testing only?
│  → nano (0.25 vCPU, 0.5 GB) or micro (0.5 vCPU, 1 GB)
├─ Small production workload?
│  → small (1 vCPU, 2 GB) — minimum recommended for production
├─ Medium traffic?
│  → medium (2 vCPU, 4 GB)
├─ High traffic?
│  → large (4 vCPU, 8 GB)
└─ Compute-intensive?
   → xlarge (8 vCPU, 16 GB)

How many nodes?
├─ Development? → 1 node (no redundancy, single point of failure)
├─ Production? → 2 nodes minimum (failover capable)
└─ Production-grade? → 3+ nodes (handles node failures gracefully)

ECR private or public image?
├─ Public registry (Docker Hub)? → No auth needed, specify image directly
└─ ECR private? → Create IAM access key with ECR read perms → pass to deployment
   → Key rotation requires a new deployment version

Need HTTPS?
  → Managed TLS is auto-provisioned for the default domain
  → For custom domain: add CNAME → Lightsail extends TLS coverage automatically
```

## Error handling

### Deployment stuck in PENDING
- Check if the container image is accessible. For ECR, verify the IAM
  access key has ECR read permissions and is not deactivated. For
  public images, verify the image exists and the tag is correct.

### Public endpoint returns 503
- Verify the container port is mapped and the container is running.
  The health check path must return HTTP 200. Check if the application
  has started successfully by viewing CloudWatch Logs.

### Health check failing
- The health check path must return HTTP 200 with the specified success
  codes. Verify the path exists and responds correctly. A path returning
  3xx (redirect) or 4xx (client error) will mark the endpoint unhealthy.

### Cannot pull from ECR
- Verify the IAM access key has `ecr:GetDownloadUrlForLayer`,
  `ecr:BatchGetImage`, and `ecr:GetAuthorizationToken` permissions.
  Check if the key has been rotated or deactivated.

## Domain

AWS CloudOps / Amazon Lightsail Container Service Provisioning &
Container Hosting.

## AWS documentation

- **Lightsail Container Service Guide** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html
- **Create container service** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-container-services.html
- **Deploy containers** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-deploying-container-services.html
- **ECR integration** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-using-container-images-ecr.html
- **Public endpoints** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services-endpoints.html
- **Custom domains** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services-custom-domains.html
- **Power scale** — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services-capacities.html
