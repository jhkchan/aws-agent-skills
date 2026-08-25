# Advanced patterns — lightsail-container-deployer

Mindset misconceptions, the configuration dependency graph, and recent AWS features, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Mindset — one-line takeaway and three misconceptions (moved from SKILL.md)

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

## Configuration dependency graph (moved from SKILL.md)

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

## Step 10 — Recent features (moved from SKILL.md)

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
