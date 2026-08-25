# Error Handling (load on demand) — CloudWatch Application Signals Operator

Operation failure triage and API error semantics moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)

### No services appearing in Application Signals
- OTel traces are not flowing. Verify the application has OTel SDK
  instrumentation or the CloudWatch Agent is configured for
  auto-instrumentation. Check trace volume in CloudWatch Service Map.

### SLI metrics not appearing
- Services may not be fully discovered yet (wait ~15 minutes). Verify
  the service is listed in Application Signals. If the service exists
  but no SLI metrics, the traces may lack the required span attributes
  (operation name, status code).

### Burn rate alarms not firing
- The SNS topic may lack subscriptions, or the alarm threshold is too
  high. Verify the SNS topic has active subscriptions. Check the burn
  rate metric value — if it is below the threshold, the SLO is healthy
  and the alarm correctly does not fire.

### SLO creation fails with "InvalidRequest"
- The interval must be 1-30 days. The target must be between 0 and 100.
  The SLI metric type must be Availability or Latency. Verify all
  parameters.

### Service map shows incomplete topology
- Trace context propagation may be missing between services. OTel
  requires W3C trace context headers to propagate across service
  boundaries. Verify the OTel propagator is configured correctly.

### RUM traces not correlating with server traces
- The RUM app monitor may not have EnableXRay set to true. Or the
  backend service may not be emitting OTel traces. Both sides must
  emit traces with matching trace IDs.
