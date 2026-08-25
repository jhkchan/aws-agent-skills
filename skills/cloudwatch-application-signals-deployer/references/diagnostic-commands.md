# Diagnostic Commands (load on demand) — CloudWatch Application Signals Deployer

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight safety checks (run before any enablement CLI) (moved from SKILL.md)

- **Confirm opt-in:** `aws application-signals list-services --region <r>`
  (200 = opted in).
- **Confirm the workload IAM role:** `aws iam list-attached-role-policies
  --role-name <role>` (must include
  `CloudWatchApplicationSignalsReportServiceAccess` and
  `AWSXrayWriteOnlyAccess`).
- **Confirm X-Ray sampling default exists:** `aws xray get-sampling-rules`
  (must list a `Default` rule with `FixedRate ≥ 0.05`).
- **Confirm the runtime is supported:** Java (JDK 8+) or Python (3.8+)
  for auto-instrumentation; other runtimes need manual OTel SDK code.
- **Confirm the service name is unique:** `aws application-signals
  list-services --query 'ServiceSummaries[?KeyAttributes.Name==\`<name>\`]'`.
- **For CloudMap enrichment:** `aws servicediscovery list-namespaces`
  to confirm the namespace exists.
