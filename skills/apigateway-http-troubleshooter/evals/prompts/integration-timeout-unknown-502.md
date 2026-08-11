# Eval prompt: integration-timeout-unknown-502

Diagnose the API Gateway HTTP API failure for the following API. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: HTTP API `api-webhook-502` returns `502 Bad Gateway` on
`POST /webhook` intermittently — about 10% of requests. GET requests
work fine.

```text
ApiId: api-webhook-502
ProtocolType: HTTP
Stage: $default

Missing context:
  - IntegrationId: not provided
  - PayloadFormatVersion: not provided
  - Integration type (Lambda vs HTTP vs VPC_LINK): not provided
  - VPC link ID: not provided
  - Execution logs: not enabled
  - Lambda logs: not checked
```

Without the integration configuration, payload format version, and
log data, it is impossible to distinguish a payload format version
mismatch, a Lambda response shape error, an integration timeout, or a
VPC link backend failure. Emit INSUFFICIENT_DATA with the specific
missing fields needed to proceed.
