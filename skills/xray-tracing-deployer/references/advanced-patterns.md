# Advanced Patterns — X-Ray Tracing Deployer

Load-on-demand deep dives moved verbatim from SKILL.md: 2024-2026 feature delta, expert heuristics, and edge-case catalog.

## Latest X-Ray features (2024-2026)
- **Lambda Powertools tracing (2024-2025):** Powertools v2 provides clean
  `@tracer.capture_lambda_handler` and `@tracer.capture_method` decorators
  for Python and TypeScript. Eliminates manual segment management. The
  recommended path for new Lambda instrumentation.
- **OpenTelemetry / ADOT Collector (2024-2025):** AWS Distro for
  OpenTelemetry (ADOT) Collector replaces the X-Ray daemon for ECS and
  EKS. Supports OTel-format traces (W3C trace context) and exports to
  X-Ray via the `awsxray` exporter. The X-Ray daemon is in maintenance
  mode — new deployments should use ADOT.
- **X-Ray sampling rule goop (2024-2025):** centralized sampling rules
  now support rule-based sampling with attributes, enabling dynamic
  sampling (e.g., sample 100% of traces with `environment=production`).
- **X-Ray Insights with anomaly detection (2024-2025):** Insights now
  detect anomalies in dependency latency (e.g., RDS slow-down) and
  surface them in the X-Ray console and EventBridge.
- **CloudWatch ServiceLens cross-account (2024-2025):** ServiceLens
  service map now aggregates traces across accounts (via CloudWatch
  cross-account observability). Previously single-account only.
- **X-Ray encryption with CMK (2024-2025):** set a customer-managed KMS
  key via `aws xray put-encryption-config`. The key must have a grant
  for the X-Ray service principal.
- **X-Ray daemon 4.x (2024-2025):** the 4.x daemon line is the final
  major version. It receives security patches only. Feature development
  has moved to ADOT Collector. Plan migration to ADOT for new deployments.
- **W3C trace context support (2024-2025):** the X-Ray SDK now supports
  W3C `traceparent` header propagation alongside the X-Ray `X-Amzn-Trace-Id`
  header. Enables interop with non-AWS tracing systems.

## Expert heuristic — choosing X-Ray SDK vs ADOT, sampling, and annotations
- **X-Ray SDK vs ADOT:** X-Ray SDK is AWS-specific and simpler (one
  package, one middleware). ADOT (OpenTelemetry) is vendor-neutral and
  supports multiple backends. For AWS-only environments, X-Ray SDK is
  faster to deploy. For multi-cloud or migration-ready architectures,
  ADOT is the future-proof choice.
- **Reservoir + Rate tuning:** reservoir = guaranteed traces/s (before
  rate applies). rate = fraction of remaining requests to sample. For
  low-traffic services (< 10 req/s), set reservoir = 1, rate = 0.05
  (default). For high-traffic critical endpoints (checkout, payment),
  set reservoir = 10, rate = 1.0 (100% above reservoir).
- **Annotation discipline:** annotate `customer_id`, `environment`,
  `region`, `feature_flag`. These are the fields you will filter on in
  the X-Ray console. NEVER annotate with high-cardinality fields (e.g.,
  `request_id`) — annotation index bloats and degrades query performance.
- **Trace context propagation:** ensure the `X-Amzn-Trace-Id` header (or
  W3C `traceparent`) is propagated across ALL service boundaries (ALB,
  API Gateway, Lambda, SQS, EventBridge). Without propagation, each
  service starts a new trace — the service map shows disconnected nodes.
- **Cost control:** X-Ray charges per trace ingested ($5 per 1M traces
  in us-east-1 as of 2026). For high-traffic services, keep the Default
  rule at 5% and use custom rules for critical endpoints. Monitor
  `GetTraceSummaries` count in CloudWatch.

## Edge-case handling
- **Cross-account tracing:** traces can span accounts via CloudWatch
  cross-account observability. The trace context (`X-Amzn-Trace-Id`)
  propagates across accounts. ServiceLens aggregates the cross-account
  service map.
- **SQS / EventBridge trace propagation:** the X-Ray SDK does NOT
  automatically propagate trace context through SQS / EventBridge. The
  producer must include the `X-Amzn-Trace-Id` header in the message
  attribute, and the consumer must read it and start a subsegment with
  the parent trace ID.
- **ECS EC2 daemon-as-a-service vs sidecar:** daemon-as-a-service (one
  daemon per EC2 instance) saves memory but requires the app to send to
  the HOST IP, not localhost. Use the ECS task metadata endpoint to
  discover the host IP, or use `AWS_XRAY_DAEMON_ADDRESS` env var.
- **EKS resource limits:** the daemon consumes CPU and memory. Set
  requests (100m CPU, 128Mi memory) and limits (500m CPU, 512Mi memory)
  on the DaemonSet. Without limits, a spike in trace volume can starve
  the app containers on the same node.
- **Lambda cold start with X-Ray:** enabling X-Ray on Lambda adds ~50-100ms
  to cold start (daemon initialization). Use Powertools to minimize
  overhead — it lazy-loads the SDK.
- **OTel migration:** the ADOT Collector replaces the X-Ray daemon.
  Switch the SDK from `aws-xray-sdk` to `opentelemetry-*` and deploy the
  ADOT Collector sidecar. The X-Ray backend is the same — only the agent
  and SDK change.
- **High-cardinality annotations:** NEVER annotate with `request_id`,
  `timestamp`, or other per-request unique fields. The annotation index
  grows unbounded and degrades X-Ray query performance. Use metadata for
  these fields.
- **X-Ray encryption with CMK:** if a CMK is set via
  `put-encryption-config`, the X-Ray service needs a grant on the key.
  If the grant is missing, `PutTraceSegments` fails silently (the daemon
  retries indefinitely).
