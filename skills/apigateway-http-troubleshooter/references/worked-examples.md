# Worked examples - API Gateway HTTP API Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — INSUFFICIENT_DATA

```text
TARGET: api abc1234 / unknown route
VERDICT: INSUFFICIENT_DATA
REASON: Symptom is 502 on POST /webhook, but integration ID,
  PayloadFormatVersion, and VPC link configuration are not provided.
  Cannot distinguish payload format mismatch, Lambda response shape
  error, or VPC link backend failure.
LAYER: UNKNOWN
EVIDENCE:
  - Symptom: POST /webhook returns 502 intermittently.
  - Missing: IntegrationId, PayloadFormatVersion, ConnectionType,
    VPC link ID, NLB target group ARN.
  - Missing: Execution logs or Lambda logs for a failing request.
REMEDIATION: Provide: (1) integration config from get-integration,
  (2) VPC link details if private integration, (3) execution logs or
  Lambda logs for a failing request, (4) confirm intermittent vs
  consistent 502.
```

