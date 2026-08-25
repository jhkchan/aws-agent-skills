---
name: lightsail-container-deployer
description: 'Provisions Amazon Lightsail Container Services with production defaults: container service creation (power scale nano/micro/small/ medium/large/xlarge), deployment (container image from ECR or public registry), public endpoint (HTTPS domain, health check path), ECR private registry auth (access key and secret), environment variables, secrets via Lightsail container parameters, scale (number of nodes), container port mapping, managed TLS certificate, custom domain via DNS CNAME, CloudWatch Logs integration, and cost predictability (all-inclusive pricing). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Lightsail container service, deploying a container, configuring ECR private auth, setting up a public endpoint, or managing scale. Triggers: create lightsail container, deploy container service, lightsail power scale, lightsail ECR auth, container public endpoint, lightsail environment variables, lightsail secrets, lightsail custom domain, lightsail managed TLS.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with lightsail access (and ECR access if pulling from a private registry). Works with Terraform aws_lightsail_container_service / aws_lightsail_container_deployment_version resources and CloudFormation via AWS::Lightsail::Container templates (where supported).'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, lightsail, container, cloudops, deploy, compute, provisioning, ecr, managed-tls, public-endpoint
  dependencies: aws-orchestrator
  keywords: aws, lightsail, container service, cloudops, deploy, provisioning, power scale, ecr auth, managed tls, public endpoint, container deployment, cost predictable
  when_to_use: Invoke when the user wants to create an Amazon Lightsail Container Service, deploy a container image (from ECR or public registry), configure ECR private registry auth, set up a public endpoint with managed TLS, configure environment variables and secrets, manage scale (node count), map container ports, or set up a custom domain. Do NOT invoke for ECS/EKS (use ECS/EKS skills), App Runner (use App Runner skills), Lambda (use Lambda skills), or Elastic Beanstalk (use Beanstalk skills).
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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Mindset — one-line takeaway and three misconceptions".
> Load when: modelling the service — power vs node count, ECR auth requirement, managed-TLS behaviour.

## Configuration dependency graph (novel heuristic)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Configuration dependency graph".
> Load when: sequencing provisioning — hard dependencies, silent failures, cross-dependency gotchas.

## Expert heuristic: power scale vs node count trade-off

> **Moved verbatim** → [references/power-and-ecr-auth.md](references/power-and-ecr-auth.md) § "Expert heuristic: power scale vs node count trade-off".
> Load when: choosing power and scale — per-node capacity ladder, replica counts, cost comparison.

## Expert heuristic: ECR private auth via access key

> **Moved verbatim** → [references/power-and-ecr-auth.md](references/power-and-ecr-auth.md) § "Expert heuristic: ECR private auth via access key".
> Load when: pulling private images — IAM key flow, required permissions, rotation semantics.

## Expert heuristic: managed TLS vs custom domain

> **Moved verbatim** → [references/endpoints-and-domains.md](references/endpoints-and-domains.md) § "Expert heuristic: managed TLS vs custom domain".
> Load when: terminating HTTPS — default-domain TLS, CNAME extension to custom domains.

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

> **Moved verbatim** → [references/endpoints-and-domains.md](references/endpoints-and-domains.md) § "Step 2 — endpoint.json template".
> Load when: creating the deployment endpoint config — container/port binding and health check.

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

> **Moved verbatim** → [references/power-and-ecr-auth.md](references/power-and-ecr-auth.md) § "Step 3 — ECR templates".
> Load when: configuring ECR private auth — the read-policy JSON, ECR containers.json, and deployment command.

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

> **Moved verbatim** → [references/endpoints-and-domains.md](references/endpoints-and-domains.md) § "Step 4 — verify public endpoint command".
> Load when: checking the endpoint after deploy — publicEndpoint query.

The endpoint URL is:
`https://<unique-id>.<region>.cs.amazonlightsail.com`

## Step 5 — Environment variables and secrets

Environment variables are plaintext in the deployment configuration.
Secrets use Lightsail's parameter system and are not visible after
creation.

> **Moved verbatim** → [references/endpoints-and-domains.md](references/endpoints-and-domains.md) § "Step 5 — environment variables template".
> Load when: configuring app variables — plaintext env vars vs parameter-backed secrets.

**Secrets (stored as parameters):**

Secrets are passed as environment variables but are not returned in
`get-container-services` responses after deployment. This provides a
layer of protection compared to plaintext environment variables.

## Step 6 — Scale (node count)

Scale determines the number of container replicas. Changing scale
triggers a rolling redeploy.

> **Moved verbatim** → [references/power-and-ecr-auth.md](references/power-and-ecr-auth.md) § "Step 6 — scale update command".
> Load when: changing node count — update-container-service rolling redeploy.

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

> **Moved verbatim** → [references/endpoints-and-domains.md](references/endpoints-and-domains.md) § "Step 8 — custom domain commands".
> Load when: adding a custom domain — endpoint lookup and Route 53 CNAME change batch.

Once the CNAME resolves, Lightsail extends the managed TLS certificate
to cover the custom domain.

## Step 9 — CloudWatch Logs integration

Lightsail Container Service can send container logs to CloudWatch Logs.
Logs include stdout/stderr from the container.

> **Moved verbatim** → [references/endpoints-and-domains.md](references/endpoints-and-domains.md) § "Step 9 — CloudWatch Logs commands".
> Load when: reading container logs — get-container-log and logs get-log-events.

## Step 10 — Recent features

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 10 — Recent features".
> Load when: checking 2023-2026 feature availability — xlarge power, ECR auth, domain auto-validation, VPC peering.

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

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example — deploy commands".
> Load when: executing the example end-to-end — create service, deploy with ECR credentials, verify endpoint, add CNAME.

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

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Error handling".
> Load when: a deployment, endpoint, health-check, or ECR pull failure occurs.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — worked-example deploy commands moved from this SKILL.md
- [references/error-handling.md](references/error-handling.md) — error-handling deep dives moved from this SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset, configuration dependency graph, and recent features moved from this SKILL.md
- [references/power-and-ecr-auth.md](references/power-and-ecr-auth.md) — power scale and ECR auth deep reference (heuristics, ECR templates, and scale command moved into this file)
- [references/endpoints-and-domains.md](references/endpoints-and-domains.md) — endpoint and domain deep reference (TLS heuristic, endpoint/env/domain/log templates moved into this file)

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
