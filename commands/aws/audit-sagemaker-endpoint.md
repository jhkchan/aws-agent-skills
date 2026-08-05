---
description: Audit a SageMaker endpoint for encryption (KMS + inter-container), execution-role blast radius, VPC config, data capture, model monitoring schedule, and instance count — emits NO_ENCRYPTION/OVERPERMISSIVE_ROLE/NO_MONITORING/PUBLIC_ENDPOINT/CONFIG_GAP/OK per endpoint.
nl_triggers:
  - "audit this SageMaker endpoint"
  - "check SageMaker endpoint encryption"
  - "is my endpoint in a VPC"
  - "endpoint execution role too broad"
  - "is model monitoring enabled"
  - "SageMaker endpoint production ready"
  - "endpoint public facing"
  - "inter-container encryption"
  - "SageMaker endpoint instance count"
  - "endpoint high availability"
  - "data capture config"
  - "model monitor schedule"
  - "hardening SageMaker endpoint"
routes_to: sagemaker-endpoint-auditor
---

# /aws:audit-sagemaker-endpoint

Activate the `sagemaker-endpoint-auditor` skill and audit one or more
SageMaker endpoint configurations (Model + EndpointConfig + Endpoint +
MonitoringSchedule) for security posture and production readiness.

## What it does

Reads a SageMaker endpoint configuration bundle — Model (ExecutionRoleArn,
VpcConfig, EnableNetworkIsolation), EndpointConfig (KmsKeyId,
EnableInterContainerTrafficEncryption, ProductionVariants, DataCaptureConfig),
Endpoint (EndpointStatus), and optional MonitoringSchedule — and applies the
ordered classification logic:

1. VPC configuration — no VpcConfig on the Model means the endpoint is
   internet-facing (PUBLIC_ENDPOINT).
2. Encryption — no KmsKeyId (NO_ENCRYPTION); inter-container encryption
   only matters for multi-container inference pipelines.
3. Execution role — wildcard actions/resources, iam:PassRole on *,
   service wildcards (OVERPERMISSIVE_ROLE).
4. Monitoring — data capture + monitoring schedule must both be present
   (NO_MONITORING if either is missing).
5. Instance count — InitialInstanceCount < 2 means no HA (CONFIG_GAP).
6. All dimensions pass → OK.

Emits a deterministic VERDICT per endpoint:

```text
ENDPOINT: <endpoint-name>
VERDICT: PUBLIC_ENDPOINT | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | NO_MONITORING | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [PUBLIC_ENDPOINT] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific CLI action per finding, or "None required" if OK>
```

## When to invoke

Paste a SageMaker endpoint configuration (Model + EndpointConfig + Endpoint
metadata) and ask any of:

- "audit this SageMaker endpoint"
- "is my endpoint encrypted?"
- "is the endpoint in a VPC?"
- "is the execution role too broad?"
- "is model monitoring enabled?"
- "is this endpoint production-ready?"
- "how many instances should I run?"

An endpoint name or ARN + any audit verb ("audit this endpoint", "check
endpoint config") also routes here via the orchestrator.

## Inputs

- Model metadata: ExecutionRoleArn, VpcConfig (Subnets + SecurityGroupIds),
  EnableNetworkIsolation, Containers/PrimaryContainer. These drive the VPC
  and IAM dimensions.
- EndpointConfig metadata: KmsKeyId, EnableInterContainerTrafficEncryption,
  ProductionVariants (InstanceType, InitialInstanceCount), DataCaptureConfig.
  These drive the encryption, monitoring, and HA dimensions.
- Endpoint metadata: EndpointStatus, EndpointType (real-time / async /
  serverless).
- MonitoringSchedule (optional): MonitoringType, Status.
- Execution-role policy document (optional but recommended for the IAM
  dimension).

## Outputs

- One VERDICT block per endpoint (multiple findings aggregate to the worst
  verdict by precedence: PUBLIC_ENDPOINT > NO_ENCRYPTION >
  OVERPERMISSIVE_ROLE > NO_MONITORING > CONFIG_GAP > OK).
- Enumerated FINDINGS list with per-finding verdict category and step number.
- Specific CLI remediation: create-model with VpcConfig, create-endpoint-config
  with KmsKeyId, scope the execution role, enable data capture + monitoring
  schedule, update instance count.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for SageMaker AI/ML endpoint security).
- `/aws:audit-kms-key-policy` for auditing the KMS key used by the endpoint
  (cross-account decrypt, rotation, deletion window).
- `/aws:audit-iam-least-privilege` for deeper IAM policy analysis of the
  execution role attached to the SageMaker Model.
