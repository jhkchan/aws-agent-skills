# Eval prompt: vpclink-nlb-config-incomplete

Diagnose the API Gateway HTTP API failure for the following API. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: HTTP API `api-vpclink-502` returns `502 Bad Gateway` on
every request to `GET /internal-api`. The integration is a private
integration via VPC link to an NLB.

```text
ApiId: api-vpclink-502
ProtocolType: HTTP
Stage: prod
AutoDeploy: true
RouteKey: GET /internal-api
IntegrationType: HTTP_PROXY
ConnectionType: VPC_LINK
ConnectionId: vpc-link-abc123
IntegrationURI: https://internal.example.com/internal-api

Missing context:
  - NLB target group ARN: not provided
  - NLB target health (describe-target-health): not provided
  - VPC link subnet IDs and SG IDs: not provided
  - NLB listener configuration: not provided
  - Whether the VPC link and NLB are in the same VPC: unknown
```

Without the NLB target group health, VPC link subnet/SG configuration,
and NLB listener details, it is impossible to determine whether the
NLB targets are unhealthy, the SG blocks traffic, the VPC link is
misconfigured, or the NLB listener is wrong. Emit INSUFFICIENT_DATA
with the specific missing fields needed to proceed.
