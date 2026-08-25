# Advanced Patterns (load on demand) — CloudWatch Application Signals Deployer

Edge-case catalog, expert-knowledge deep dives, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Edge-case handling (moved from SKILL.md)

- **Service missing from service map after 15 min:** 90% of cases are
  missing `CloudWatchApplicationSignalsReportServiceAccess` on the task
  role. Check the CloudWatch Logs group
  `/aws/application-signals/<service>` for `AccessDenied`.
- **RED metrics blank but traces visible in X-Ray:** sampling rule is
  set to 0%, or the Default rule was deleted. Recreate per Step 5.
- **Multiple services collapse into one node:** `AWS_SERVICE_NAME` is
  identical across services, or unset (defaults to image name). Set
  unique `AWS_SERVICE_NAME` per workload.
- **SLO creation fails with `ServiceNotFound`:** the SLO resource
  references a service key that hasn't been discovered yet. Wait for
  the service to appear in `ListServices` before creating the SLO.
- **Lambda auto-instrumentation fails silently:** the ADOT Lambda layer
  ARN must match the runtime architecture (`x86_64` vs `arm64`). Check
  the layer version in the Lambda configuration.
- **EKS mutating webhook does not inject:** the namespace must have the
  `instrumentation.opentelemetry.io/inject-java: "true"` annotation
  (or the pod template spec). The operator namespace must exist.
- **Custom metric SLO:** custom metrics require a
  `RequestBasedSliConfig` with both `GoodRequestsMetric` and
  `TotalRequestsMetric` math expressions. Reference the
  `AWS/ApplicationSignals` namespace, not custom namespaces.
---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Application Signals for Lambda GA (2024-2025):** the
  `aws-otel-lambda-python` and `aws-otel-lambda-java` layers expose
  Lambda functions in the service map without manual OTel SDK code.
  Layer ARN is Region-specific.

- **Application Signals for ECS GA (2024-2025):** sidecar pattern
  documented and supported. Previously EKS-only.

- **`AWS::ApplicationSignals::ServiceLevelObjective` CloudFormation
  GA (2024-2025):** native SLO resource with `PeriodBased` and
  `RequestBased` SLI configs, rolling intervals, and built-in burn-rate
  metrics. Replaces the prior CLI-only flow.

- **Python auto-instrumentation GA (2024-2025):** the OTel Operator
  Python injection annotation
  (`instrumentation.opentelemetry.io/inject-python`) reached GA. Java
  and Python are now the two supported auto-instrumentation languages.

- **Burn-rate alarm automation (2024-2025):** `BurnRates` in the SLO
  `Goal.Interval` automatically publishes derived `BurnRate` metrics —
  no custom metric math needed.

- **Service map cross-account (2025):** services discovered in accounts
  sharing a CloudWatch cross-account observability link appear in the
  monitoring account's service map.

- **CloudWatch RUM client-side correlation (2025):** RUM web app
  sessions can be joined to server-side Application Signals service
  nodes via the `AWS/ApplicationSignalsClient` namespace.

- **SLO warning threshold (2025):** `WarningThreshold` in the SLO `Goal`
  emits a separate warning state before the SLO breaches.
---

## Expert heuristic — enabling signals and choosing SLOs (moved from SKILL.md)

- **IAM policies first, instrumentation second.** The agent runs with
  or without permissions; only the IAM policies enable output. Verify
  with `list-services` within 10 minutes of deployment.
- **Default to Java or Python auto-instrumentation.** Other runtimes
  (Node, Go, .NET) require manual OTel SDK code — auto-instrumentation
  is not GA for these.
- **One SLO per service, two at most.** Availability and p95 latency
  cover 90% of use cases. Adding more SLOs fragments attention and
  alarm budget.
- **Burn-rate thresholds are universal.** 14.4×/5m, 6×/1h, 3×/6h, 1×/1d
  map to "page on 2% budget burn", "page on 10%", "ticket on 10%",
  "ticket on drain". Apply consistently.
- **Sampling rate vs. SLO accuracy.** A 5% sampling rate gives
  sufficient resolution for p95 latency above 50 RPS. For
  lower-traffic services, raise to 50-100% to avoid noisy RED
  aggregates.
- **Service name discipline.** Set `AWS_SERVICE_NAME` to the workload
  name, not the team or the environment. Use
  `AWS_APPLICATION_ENVIRONMENT` for environment separation.
- **Cross-Region:** Application Signals does not merge across Regions.
  Plan per-Region SLOs and per-Region burn-rate alarms.
