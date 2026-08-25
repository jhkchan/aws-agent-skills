# Advanced Patterns (load on demand) — App Runner Service Deployer

Edge-case catalogs and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Latest App Runner features (2024-2026) (moved from SKILL.md)

- **VPC ingress connection (2024-2025):** allows clients in a private VPC
  to reach an App Runner service via AWS PrivateLink WITHOUT traversing
  the public internet. Configure with
  `aws apprunner create-vpc-ingress-connection`. This is the long-awaited
  "private endpoint" feature for App Runner.
- **Application Load Balancer integration (2024-2025):** App Runner
  services can now front an ALB for advanced routing (weighted target
  groups, path-based routing, sticky sessions). Previously only the
  managed App Runner endpoint was available.
- **ARM64 / Graviton support (2024-2025):** set `CpuArchitecture=ARM64`
  for up to 20% price-performance. The ECR image MUST be ARM64.
- **Manual deployments with pause/resume (2024-2025):** set
  `AutoDeploymentsEnabled=false` to pause automatic deployments. Trigger
  a manual deployment with `aws apprunner start-deployment`. Useful for
  controlled rollout windows and change-management compliance.
- **Observability configuration (2024-2025):** dedicated
  `ObservabilityConfiguration` resource for X-Ray tracing toggle without
  embedding it in the service definition.
- **Private worker mode (2024-2025):** services with no public endpoint,
  reachable only via VPC ingress. Eliminates the need for a "deny all"
  security group workaround.
- **Deployment priority queues (2024-2025):** concurrent deployments in
  the same account are queued. The service displays `OperationInProgress`
  status. Use `list-operations` to track progress.
- **Enhanced health checks (2024-2025):** TCP probe type for non-HTTP
  services. Previously only APP (HTTP) probe was available.

---

## Edge-case handling (moved from SKILL.md)

- **Cross-account ECR pull:** the access role needs
  `ecr:BatchGetImage` on the cross-account repo AND the repo policy in
  the other account must grant your root. The managed
  `AWSAppRunnerServicePolicyForECRAccess` does NOT cover cross-account —
  add an inline policy.
- **VPC connector sharing:** a VPC connector can be attached to multiple
  services, but the ENI pool is shared. For high-throughput workloads,
  create a dedicated connector per service.
- **Private endpoint mode:** set the network egress type to `VPC` and
  create a VPC ingress connection in the consumer VPC. The service has
  no public URL — only the PrivateLink endpoint.
- **Slow-start JVM tasks:** set `unhealthyThreshold=5` and
  `interval=10s` to give the JVM 50s to start before being marked
  unhealthy. For very slow starts, consider `StartCommand` with a
  readiness probe wrapper.
- **Source code repository build failures:** App Runner builds the image
  from source if `ImageRepositoryType=ECR` is not set. Build failures
  show up in `list-operations` as `OperationType=CREATE_SERVICE` with
  `Status=FAILED`. Check the build logs in CloudWatch under
  `/aws/apprunner/<service>/build`.
- **Auto-deployment surprises:** `AutoDeploymentsEnabled=true` means
  every push to the source branch triggers a deployment. For production,
  use `false` and trigger `start-deployment` after review.
- **Log group naming:** the log group is `/aws/apprunner/<service-name>`
  (NOT the service ARN). If you rename the service, the log group does
  NOT follow — old logs stay under the old name.
