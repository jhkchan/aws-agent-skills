# Source and Configuration Guide — App Runner Service Deployer

Deep reference on source type selection (ECR vs code repository), VPC
connector networking, auto-scaling tuning, health check policy,
observability, custom domains, the full NEVER list, edge-case handling,
and pre-flight safety CLI.

## Source type selection — ECR image vs source code repository

### ECR image (recommended for production)

| Aspect | Detail |
|---|---|
| `ImageRepositoryType` | `ECR` |
| Build pipeline | YOU build and push the image. Full control. |
| Deploy speed | Fast (~30-60s) — no build step. |
| Access role REQUIRED | Yes — `AWSAppRunnerServicePolicyForECRAccess` managed policy. |
| Use when | Production, regulated environments, multi-stage build pipelines, images shared across compute platforms. |

```json
{
  "ImageRepository": {
    "ImageIdentifier": "<acct>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {"Port": "8080"}
  },
  "AuthenticationConfiguration": {
    "AccessRoleArn": "arn:aws:iam::<acct>:role/<access-role>"
  }
}
```

### Source code repository (rapid prototyping)

| Aspect | Detail |
|---|---|
| `CodeRepository.RepositoryUrl` | GitHub, GitLab, Bitbucket via CodeConnections. |
| Build pipeline | App Runner builds the image for you. Limited control. |
| Deploy speed | Slow (~3-8 min) — includes build step. |
| Connection ARN REQUIRED | Yes — `aws codeconnections create-connection`. |
| Use when | Prototyping, small teams without a container build pipeline, hackathons. |

```json
{
  "CodeRepository": {
    "RepositoryUrl": "https://github.com/org/<repo>",
    "SourceCodeVersion": {"Type": "BRANCH", "Value": "main"},
    "CodeConfiguration": {
      "ConfigurationSource": "API",
      "CodeConfigurationValues": {
        "Runtime": "nodejs20",
        "BuildCommand": "npm install",
        "StartCommand": "node server.js",
        "Port": "8080"
      }
    }
  }
}
```

Supported runtimes: `python3` (3.10+), `nodejs20` (and later),
`corretto17` / `corretto21` (Java), `go1` (Go 1.x), `php81` (PHP 8.1+),
`dotnet7` (and later).

**NEVER use source code repository source for production unless your team
has a strong reason.** The build pipeline is opaque, you cannot inject
build-time secrets easily, and build failures surface only after a push.

## VPC connector networking deep dive

### Why the VPC connector matters

Without a VPC connector, App Runner instances run in an AWS-managed VPC
with internet access but NO private VPC access. This means:

- **RDS, Aurora, ElastiCache:** DNS resolves but TCP connections hang
  until timeout. This is the #1 silent-failure pitfall.
- **Internal ALBs / NLBs:** unreachable.
- **VPC-only AWS services** (e.g., Interface VPC endpoints for private
  APIs): unreachable.

### VPC connector ENI lifecycle

Each VPC connector creates a pool of ENIs in the specified subnets. The
ENI count scales with the number of App Runner instances attached to the
connector. Rules:

- **Use PRIVATE subnets only.** App Runner instances do not need public
  IPs — the connector routes egress through the VPC.
- **Span >= 2 AZs** (3 for production HA). A connector in a single AZ is
  a single point of failure.
- **Security group outbound** must allow the database port:
  - PostgreSQL: 5432/tcp
  - MySQL/Aurora: 3306/tcp
  - Redis/ElastiCache: 6379/tcp
  - MongoDB: 27017/tcp
- **NAT Gateway is NOT required.** The connector uses AWS PrivateLink
  internally. Do NOT add a NAT Gateway just for the App Runner connector.
- **Subnet IP capacity:** each connector consumes IPs from the subnet.
  Use a /24 or larger subnet. Avoid /28 (16 IPs) — the connector may
  exhaust available IPs.

### VPC ingress connection (private endpoint mode)

For services that should NOT be reachable from the public internet:

```bash
# Consumer side — creates a PrivateLink endpoint in the consumer VPC
aws apprunner create-vpc-ingress-connection \
  --vpc-ingress-connection-name <service>-ingress \
  --service-arn <service-arn> \
  --ingress-vpc-configuration '{
    "VpcId": "vpc-xxx",
    "VpcEndpointId": "vpce-xxx"
  }'
```

The service URL resolves only within the consumer VPC. This is the
solution for "App Runner in a private subnet" — previously required a
"deny all" security group workaround.

### VPC connector sharing

A VPC connector can be attached to multiple services. However:

- The ENI pool is SHARED across all attached services.
- High-throughput services may exhaust the ENI pool, causing connection
  failures for other services.
- For production, create a DEDICATED connector per high-throughput
  service.

## Auto-scaling tuning

### How App Runner scaling works

App Runner scales based on **concurrent requests per instance**, NOT CPU
utilization. When the number of concurrent requests to an instance
exceeds `max-concurrency`, App Runner provisions a new instance.

| Parameter | Effect | Production range |
|---|---|---|
| `min-size` | Baseline always-warm instances | 2 (HA), 0 (dev) |
| `max-size` | Cap on instances (cost control) | 6-20 |
| `max-concurrency` | Requests per instance before scale-out | 50-200 |

### Concurrency tuning by workload

| Workload | `max-concurrency` | Rationale |
|---|---|---|
| CPU-heavy (ML inference, image processing) | 10-50 | Each request saturates CPU |
| Standard API (Node.js, Python) | 100 | I/O-bound, handles many concurrent |
| JVM (Spring Boot) | 50-100 | Thread pool limits concurrency |
| Streaming / WebSocket | 20-50 | Long-lived connections hold instances |

### Scale-to-zero

`min-size=0` allows the service to scale to zero when idle. Trade-offs:

- **Cost:** zero cost when idle (you pay only for the connector ENIs).
- **Cold start:** 30-60 seconds for the first request. User-facing
  endpoints MUST NOT scale to zero.
- **Use cases:** dev/staging, batch processing endpoints, internal tools
  with low traffic.

### Provisioned concurrency

`min-size >= 1` guarantees at least one warm instance. This is the ONLY
latency guarantee in App Runner. For user-facing production services, set
`min-size >= 2` for HA across AZs.

## Health check policy

### Probe types

| Type | Protocol | What it detects |
|---|---|---|
| `APP` | HTTP | App-level health (returns HTTP 200 on `/healthz`) |
| `TCP` | TCP | Port is open (catches process crashes, NOT app unhealthiness) |

**Always prefer `APP` probe for HTTP services.** TCP probe misses
app-level unhealthiness (e.g., DB connection pool exhausted, deadlock).

### Threshold tuning

| Parameter | Default | Production | Effect |
|---|---|---|---|
| `IntervalInSeconds` | 10 | 10 | Time between probes |
| `TimeoutInSeconds` | 5 | 5 | Probe timeout |
| `HealthyThreshold` | 3 | 3 | Consecutive successes to mark healthy |
| `UnhealthyThreshold` | 5 | 5 | Consecutive failures to mark unhealthy |

**NEVER set `UnhealthyThreshold < 3`.** Transient network blips (DNS
hiccup, brief CPU spike) cause spurious rollbacks. The default of 5
gives the app ~50s to recover before being marked unhealthy.

### Health check path alignment

The health check path MUST return HTTP 200 when the app is ready to serve
traffic. Common patterns:

- **Node.js / Express:** `app.get('/healthz', (req, res) => res.status(200).send('ok'))`
- **Java / Spring Boot:** use `/actuator/health` (built-in)
- **Python / Flask:** `@app.route('/healthz') def health(): return 'ok', 200`
- **Go:** `http.HandleFunc('/healthz', func(w, r) { w.WriteHeader(200) })`

The health check endpoint should do a LIGHTWEIGHT check (process is
alive, event loop is responsive). NEVER do a deep dependency check (DB,
downstream API) in the health check — that causes cascading failures.

## Observability configuration

### CloudWatch Logs

- **Log group name:** `/aws/apprunner/<service-name>/<service-id>`
  (NOT configurable — derived from service name).
- **Retention:** App Runner creates the log group with `Never Expire` if
  it does not exist. Pre-create with the desired retention.
- **Log stream:** one per instance. Instances are ephemeral, so log
  streams accumulate. Use CloudWatch Logs Insights for querying.

### X-Ray tracing

Set `TracingConfiguration Vendor=AWSXRay` on the observability
configuration. The instance role needs:

```json
{
  "Effect": "Allow",
  "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
  "Resource": "*"
}
```

X-Ray tracing auto-instruments the HTTP layer for Java (Tomcat, Jetty),
Python (Django, Flask), and Node.js (Express). No code changes required
for incoming-request tracing. For outgoing SDK calls, add the X-Ray SDK
to your code.

### Application Signals

When X-Ray tracing is enabled, Application Signals auto-discovers SLOs
and generates latency / error-rate metrics. Available in the CloudWatch
console under "Application Signals". No additional configuration needed.

## Custom domain

### Managed TLS

App Runner provisions and manages the TLS certificate via AWS Certificate
Manager (ACM). The certificate auto-renews. No manual intervention.

### Route 53 integration

If your domain is in Route 53, App Runner auto-creates the CNAME records.
For domains in other DNS providers, you must add the CNAME records
manually.

### Wildcard and www

Set `enable-www-subdomain=true` to also map `www.<domain>`. This creates
a separate certificate SAN for the www variant.

## Full NEVER list (12 items)

1. NEVER use `:latest` image tag in production. Pin to a version tag or
   SHA digest. App Runner auto-deploys new `:latest` pushes without
   warning.
2. NEVER conflate the ECR access role and the instance role. They serve
   different purposes (image pull vs app identity).
3. NEVER deploy without a VPC connector when the app connects to private
   VPC resources (RDS, ElastiCache, internal ALBs).
4. NEVER set `unhealthyThreshold < 3`. Transient blips cause spurious
   rollbacks.
5. NEVER use the default auto-scaling (`min-size=1`) for production
   user-facing services. Set `min-size >= 2` for HA.
6. NEVER use source code repository source for production unless your
   team has a strong reason. The build pipeline is opaque.
7. NEVER put secrets in `RuntimeEnvironmentVariables` (plaintext). Use
   `RuntimeEnvironmentSecrets` with ARN references.
8. NEVER use `AdministratorAccess` on the access role or instance role.
9. NEVER share a VPC connector across high-throughput services. Create a
   dedicated connector per service.
10. NEVER use `AutoDeploymentsEnabled=true` for production without a
    change-management process. Every push triggers a deployment.
11. NEVER assume the CloudWatch log group has retention set. App Runner
    creates it with `Never Expire` if it does not exist.
12. NEVER use a single-AZ VPC connector for production. A connector in a
    single AZ is a single point of failure.

## Pre-flight safety CLI

```bash
# ECR image exists
aws ecr describe-images \
  --repository-name <repo> \
  --image-ids imageTag=<tag> \
  --query 'imageDetails[0].imageTags'

# Access role trusts App Runner
aws iam get-role --role-name <access-role> \
  --query 'Role.AssumeRolePolicyDocument.Statement[0].Principal.Service'

# Instance role has app permissions
aws iam list-attached-role-policies --role-name <instance-role>
aws iam list-role-policies --role-name <instance-role>

# VPC connector is ACTIVE
aws apprunner describe-vpc-connector \
  --vpc-connector-arn <vc-arn> \
  --query 'VpcConnector.Status'

# Secrets resolve
aws secretsmanager describe-secret --secret-id <id>
aws ssm get-parameter --name <name> --with-decryption

# Log group retention is set
aws logs describe-log-groups \
  --log-group-name-prefix /aws/apprunner/<service> \
  --query 'logGroups[0].retentionInDays'

# Service quota remaining
aws service-quotas get-service-quota \
  --service-code apprunner \
  --quota-code L-DBB8PPEX
```

## Edge cases

- **Cross-account ECR pull:** the managed policy
  `AWSAppRunnerServicePolicyForECRAccess` covers same-account ECR. For
  cross-account, add an inline policy granting `ecr:BatchGetImage` on the
  cross-account repo ARN AND ensure the repo policy grants your account.
- **VPC connector IP exhaustion:** each connector consumes IPs. In a /28
  subnet (16 IPs), the connector may exhaust available IPs. Use a /24 or
  larger subnet.
- **Private endpoint + custom domain:** when using VPC ingress (private
  endpoint), the custom domain resolves to the PrivateLink endpoint IP.
  The managed TLS certificate covers both the public and private URLs.
- **Slow-start JVM tasks:** set `unhealthyThreshold=5` and
  `interval=10s`. For Spring Boot, the default `/actuator/health` check
  returns 200 only after the context is fully loaded.
- **Source code build failures:** check CloudWatch under
  `/aws/apprunner/<service>/build` for build logs. The build uses the
  runtime specified in `CodeConfigurationValues.Runtime`.
- **Deployment queue:** concurrent deployments are queued. The service
  shows `OperationInProgress`. Use `list-operations` to track progress.
- **Pause/resume:** `pause-service` stops billing for compute but the
  VPC connector ENIs remain (small charge). `resume-service` restarts
  the service.
