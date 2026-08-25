# Advanced Patterns (load on demand) — App Runner Autoscaling Optimizer

Step 0 expert-knowledge deep dives and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious App Runner autoscaling behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational App Runner
experience. Each changes a recommendation if ignored:

- **Concurrency is the primary lever, not instance type.** Doubling
  concurrency from 50 to 100 halves the instance count for the same traffic.
  This saves ~50% of compute cost. Doubling the instance type (1 vCPU to 2
  vCPU) doubles the per-instance cost but does not reduce instance count
  (the autoscaler still provisions based on concurrency). The only reason
  to increase instance type is if the higher concurrency would cause
  CPU/memory exhaustion on the smaller instance.

- **Scale-to-zero (MinSize 0) eliminates idle cost.** App Runner bills
  per-second for on-demand usage (requests being processed). With MinSize 0
  and no traffic, the service scales to zero and compute charges stop. The
  tradeoff is cold-start latency on the first request after idle (typically
  5-30 seconds depending on container image size).

- **MinSize >= 1 means always-provisioned billing.** Each provisioned
  instance is billed per-hour regardless of traffic. A MinSize of 2 on a
  1 vCPU/2 GB service costs $0.126/hr * 730 hr/month = ~$92/month in idle
  compute. If the service has predictable business-hours traffic, set
  MinSize to 0 and accept the cold start, or set MinSize to 1 for a
  balance.

- **App Runner concurrency is not the same as Lambda concurrency.** Lambda
  concurrency = number of simultaneous invocations. App Runner concurrency
  = number of simultaneous HTTP requests per instance. The total concurrent
  capacity = instance count * concurrency setting. The autoscaler adjusts
  instance count to keep concurrent requests per instance at or below the
  concurrency setting.

- **Higher concurrency increases latency.** At concurrency 100, a single
  instance handles 100 simultaneous requests. If each request is CPU-bound
  (1 second of processing), the effective latency is ~100 seconds (serial
  processing on 1 vCPU) unless the workload is I/O-bound (async I/O allows
  true concurrency). Benchmark with realistic load before increasing
  concurrency.

- **Deployment pauses autoscaling.** During a deployment, App Runner
  replaces instances with the new version. The autoscaler does not add or
  remove instances during this window. High-traffic deployments may
  temporarily increase latency because the new instances start from zero.

- **Health check interval affects scale-out speed.** App Runner checks
  instance health every `Interval` seconds. If an instance becomes
  unhealthy, the service waits `Interval * UnhealthyThreshold` seconds
  before replacing it. A 1-second interval with 5 unhealthy-threshold = 5
  seconds detection. A 10-second interval = 50 seconds detection. Tune
  for your workload's tolerance.

- **Scale-in cooldown (default 60s) prevents flapping.** After the
  autoscaler removes an instance, it waits 60 seconds before removing
  another. This prevents rapid scale-in/scale-out cycles (flapping) on
  bursty traffic. A longer cooldown saves cost (instances stay longer at
  lower counts) but delays response to traffic drops. A shorter cooldown
  saves less but responds faster.

- **VPC egress cost via NAT gateway.** If the App Runner service uses a
  VPC connector to access private resources (RDS, ElastiCache, internal
  APIs), all outbound traffic from the VPC to the internet goes through
  the NAT gateway at $0.045/GB processed + $0.045/GB data transfer. For
  high-egress workloads, this can exceed the compute cost. Use VPC
  endpoints for AWS service traffic (S3, DynamoDB, SQS, etc.) to bypass
  the NAT gateway.

- **Custom domain SSL has negligible compute overhead.** App Runner
  manages the certificate (via AWS Certificate Manager) and terminates
  TLS at the load balancer. The TLS handshake adds < 1ms per request.
  No optimization needed for custom domains.

- **Observability cost from CloudWatch Logs.** App Runner sends
  application logs to CloudWatch Logs by default. For high-traffic
  services, log ingestion can be significant (~$0.50/GB ingested). If
  the service logs verbose output (request/response bodies, debug logs),
  reducing log verbosity or sampling can save observability cost.

- **Pause/resume is not scale-to-zero.** Pausing a service stops all
  compute and removes the endpoint. The service configuration is
  preserved; resuming recreates the endpoint. Pause/resume is for non-
  prod environments (dev/staging/QA) that are not needed outside business
  hours. Scale-to-zero (MinSize 0) is for production services that should
  stay accessible but handle zero-traffic periods.

- **MaxSize limits burst capacity.** If MaxSize is too low, the autoscaler
  cannot provision enough instances during traffic spikes, and requests
  queue or fail with 5xx. If MaxSize is too high, the autoscaler may
  provision excessively during misconfigured scaling policies. Set MaxSize
  to 2-3x the peak observed instance count.

- **Cost-per-request analysis reveals efficiency.** Total monthly cost /
  total monthly requests = cost per request. For a $1,200/month service
  handling 8M requests, that is $0.00015/request. Benchmark against
  alternative platforms (Lambda + API Gateway, ECS/Fargate, EC2) to
  determine if App Runner is the right platform.

- **Auto-scaling configuration is versioned.** `create-auto-scaling-
  configuration` creates a new version. You then `update-service` with the
  new ARN. Old configurations can be deleted once no service references
  them.

- **App Runner v2 eliminates the VPC connector requirement for private
  networking.** The v2 architecture (2025 GA) gives each service a
  native ENI in your VPC without provisioning a separate VPC connector
  resource. This removes the connector's NAT gateway dependency for
  outbound traffic and reduces egress cost by up to 60% for
  high-egress services. Services still on the v1 architecture must
  explicitly migrate; existing VPC connectors continue to work but
  are not eligible for the cost reduction. Check `NetworkConfiguration.
  EgressConfiguration` — v2 services show `EgressType: VPC` without a
  `VpcConnectorArn`.

- **The autoscaler uses a Kubernetes-style HPA algorithm under the
  hood.** App Runner runs containers on a managed Kubernetes cluster.
  The autoscaler computes desired instance count as `desired =
  ceil(currentConcurrentRequests / concurrencySetting)`, then applies
  a stabilization window (default 60 seconds for scale-in, immediate
  for scale-out). Burst traffic within a 60-second window may not
  trigger scale-in even if the concurrent request count drops — the
  autoscaler waits to confirm the drop is sustained. This explains
  why `InstanceCount` does not track `RequestCount` perfectly in
  real-time; the stabilization window introduces lag on scale-in.

- **The concurrency-vs-CPU-utilization trade-off follows a non-linear
  curve.** Below ~70% CPU utilization, increasing concurrency yields
  near-linear cost savings (fewer instances, same throughput). Above
  ~70% CPU, the OS scheduler overhead grows super-linearly: context-
  switching and memory pressure cause per-request latency to spike
  2-3x even though throughput is maintained. The sweet spot for CPU-
  bound workloads is 50-65% CPU utilization at the target concurrency.
  For I/O-bound workloads (API calls, DB queries), the ceiling is
  higher (~80% CPU) because threads spend time blocked on network I/O,
  not consuming CPU cycles. Check `CPUUtilization` at the current
  concurrency before recommending an increase.

- **Pause/resume has a hidden cost beyond zero compute.** Resuming a
  paused service pulls the container image from ECR again (cold pull,
  not cached), taking 30-120 seconds depending on image size. For
  images > 500 MB, the resume delay can exceed 2 minutes.
  Additionally, the first few requests after resume have elevated
  latency (~2x p95) as the JIT compiler and connection pools warm up.
  For dev/staging environments, schedule resume 5 minutes before the
  team needs access. The ECR data transfer for re-pulling is typically
  <$1/month but is not zero.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **App Runner v2 native VPC networking (2025 GA):** The v2
  architecture provisions a native ENI per service in your VPC without
  a separate VPC connector resource. Eliminates the NAT gateway
  dependency for outbound traffic, reducing egress cost by up to 60%.
  Existing v1 services must explicitly migrate. Check
  `NetworkConfiguration.EgressConfiguration` for `EgressType: VPC`
  without `VpcConnectorArn`.

- **VPC connector for private resources (2024 GA):** App Runner services
  can connect to private VPC resources (RDS, ElastiCache, internal APIs)
  via a VPC connector. Egress traffic goes through the VPC's NAT gateway
  unless VPC endpoints are configured.

- **Custom auto-scaling configurations (2024):** Create reusable auto-
  scaling configurations with specific MinSize, MaxSize, and Concurrency.
  Attach to multiple services for consistent scaling behavior.

- **Observability configuration (2024-2025):** Configure CloudWatch Logs
  ingestion rate, log format (JSON vs text), and trace sampling (AWS X-Ray).
  Reducing log verbosity lowers observability cost for high-traffic services.

- **Size-aware health checks (2025):** Health check grace period for new
  instances during scale-out. The service waits for the grace period before
  checking health, giving the instance time to warm up.

- **Deployment strategies (2025):** Rolling deployment (default) replaces
  instances gradually. Blue/green deployment creates a new fleet, switches
  traffic, then tears down the old fleet. Blue/green avoids the deployment-
  pauses-autoscaling issue.

- **Cost allocation tags (2024-2025):** Tag App Runner services with cost
  allocation tags for Cost Explorer filtering. Essential for multi-service
  cost attribution.

- **App Runner observability dashboard (2025):** A pre-built CloudWatch
  dashboard for App Runner services showing RequestCount, InstanceCount,
  CPU/Memory utilization, latency, and error rates. Useful for identifying
  optimization opportunities without manual metric queries.
