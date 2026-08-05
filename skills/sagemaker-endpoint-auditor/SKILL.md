---
name: sagemaker-endpoint-auditor
description: >-
  Audits SageMaker real-time and async endpoints for security posture and
  production readiness — KMS encryption-at-rest and inter-container traffic
  encryption, execution-role blast radius (wildcard actions, sagemaker:*,
  iam:PassRole), VPC configuration (internet-facing vs private), data capture
  and model monitoring schedule coverage, and instance count for high
  availability. Emits a deterministic verdict
  (NO_ENCRYPTION | OVERPERMISSIVE_ROLE | NO_MONITORING | PUBLIC_ENDPOINT |
  CONFIG_GAP | OK) per endpoint with enumerated findings and CLI remediation.
  Use when reviewing SageMaker endpoints before production deployment,
  checking endpoint encryption posture, auditing execution-role scope,
  validating VPC configuration, verifying model monitoring coverage, or
  checking instance count for high availability.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config-document classification.
  Live-account audits use aws sagemaker describe-endpoint,
  describe-endpoint-config, describe-model, and list-monitoring-schedules
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - SageMaker
  - endpoint
  - KMS encryption
  - inter-container encryption
  - execution role
  - VPC config
  - data capture
  - model monitor
  - instance count
  - high availability
  - production readiness
  - endpoint audit
  - inference pipeline
  - network isolation
  - sagemaker:InvokeEndpoint
  - blast radius
tags: [sagemaker, ai-ml, security, endpoint, encryption, vpc, monitoring, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  verdict_shape: "NO_ENCRYPTION | OVERPERMISSIVE_ROLE | NO_MONITORING | PUBLIC_ENDPOINT | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a SageMaker endpoint before production deployment, checking
    endpoint encryption (KMS + inter-container), auditing the execution role
    for wildcard permissions, validating VPC configuration (private vs
    internet-facing), verifying model monitoring coverage (data capture +
    monitoring schedule), or checking instance count for high availability.
  activation_triggers:
    - "audit this SageMaker endpoint"
    - "is my endpoint encrypted"
    - "check endpoint VPC config"
    - "execution role too broad"
    - "is model monitoring enabled"
    - "endpoint production ready"
    - "SageMaker endpoint public"
    - "inter-container encryption"
  invocation_schema: >-
    Input: either (a) a SageMaker endpoint configuration bundle (Model +
    EndpointConfig + Endpoint metadata + optional MonitoringSchedule +
    optional execution-role policy document), OR (b) an endpoint name/ARN for
    live-account audit. Output: deterministic ENDPOINT/VERDICT/REASON/FINDINGS/
    REMEDIATION block per endpoint, where VERDICT is one of NO_ENCRYPTION,
    OVERPERMISSIVE_ROLE, NO_MONITORING, PUBLIC_ENDPOINT, CONFIG_GAP, OK.
---

# SageMaker Endpoint Auditor

## Mindset

**One-line takeaway:** a SageMaker endpoint is a running model exposed behind
an invocation API. Its security posture is the intersection of **three
independent resource objects** — the Model, the EndpointConfig, and the
Endpoint — and the most common audit mistake is checking only one of them.

A SageMaker real-time endpoint is not a single object. The security-relevant
fields are split across a resource chain:

- **Model** (`DescribeModel`) — holds `ExecutionRoleArn` (the IAM role the
  container assumes), `VpcConfig` (network placement), `EnableNetworkIsolation`
  (container egress control), and the container image spec.
- **EndpointConfig** (`DescribeEndpointConfig`) — holds `KmsKeyId` (encryption
  at rest), `ProductionVariants` (instance type + count), `DataCaptureConfig`
  (request/response capture for monitoring), and
  `EnableInterContainerTrafficEncryption`.
- **Endpoint** (`DescribeEndpoint`) — holds `EndpointStatus` (InService /
  Updating / Failed), `FailureReason`, and the resolved variant instance counts.
- **MonitoringSchedule** (`ListMonitoringSchedules`) — optionally attached to
  the endpoint for drift detection (data quality, model quality, bias,
  explainability).

An audit that checks only the EndpointConfig misses the execution role and VPC
placement (both live on the Model). An audit that checks only the Model misses
encryption and data capture (both live on the EndpointConfig). **Always resolve
the full chain.**

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| No `VpcConfig` on the Model (endpoint is internet-facing) | **PUBLIC_ENDPOINT** | 1 |
| `VpcConfig` present but `SecurityGroupIds` allow `0.0.0.0/0` inbound | **PUBLIC_ENDPOINT** | 1 |
| No `KmsKeyId` on EndpointConfig | **NO_ENCRYPTION** | 2 |
| Inference pipeline (multi-container) + `EnableInterContainerTrafficEncryption: false` | **NO_ENCRYPTION** | 2 |
| Execution role with `Action: "*"` on `Resource: "*"` | **OVERPERMISSIVE_ROLE** | 3 |
| Execution role with `sagemaker:*` / `s3:*` / `iam:*` on `"*"` | **OVERPERMISSIVE_ROLE** | 3 |
| Execution role with `iam:PassRole` on `"*"` | **OVERPERMISSIVE_ROLE** | 3 |
| No `DataCaptureConfig` (or `EnableCapture: false`) AND no `MonitoringSchedule` | **NO_MONITORING** | 4 |
| `EnableCapture: true` but `InitialSamplingPercentage: 0` | **NO_MONITORING** | 4 |
| `InitialInstanceCount < 2` (single instance — no HA) | **CONFIG_GAP** | 5 |
| All dimensions pass | **OK** | 6 |

**Precedence (worst finding wins):**
PUBLIC_ENDPOINT > NO_ENCRYPTION > OVERPERMISSIVE_ROLE > NO_MONITORING > CONFIG_GAP > OK

## Pre-flight: endpoint metadata gate

Before evaluating the endpoint configuration, classify the endpoint state.
Several endpoint attributes short-circuit the audit.

| Attribute | Value | Effect on audit |
|---|---|---|
| `EndpointStatus` | `InService` | Proceed with full audit. |
| `EndpointStatus` | `Updating` | Proceed, but note that config may be mid-change. Re-audit after update completes. |
| `EndpointStatus` | `Failed` | Endpoint deployment failed. Note `FailureReason`. Still audit the config (the security findings may explain the failure). |
| `EndpointStatus` | `Deleting` | Endpoint is being torn down. Audit for forensic record only. |
| Endpoint type | Real-time | Full audit applies. |
| Endpoint type | Async | Full audit + check `AsyncInferenceConfig.OutputConfig.S3OutputPath` is encrypted (KMS on the bucket). |
| Endpoint type | Serverless | No instance count dimension (scale-to-zero). Skip Step 5 instance-count check. VPC config still applies. |

**If the configuration bundle is incomplete** (missing Model, EndpointConfig,
or Endpoint metadata), output:

```text
ENDPOINT: <name>
VERDICT: ERROR
REASON: Cannot resolve the full Model -> EndpointConfig -> Endpoint resource chain — <missing object>.
REMEDIATION: Retrieve all three objects: aws sagemaker describe-model --model-name <name>, aws sagemaker describe-endpoint-config --endpoint-config-name <config>, aws sagemaker describe-endpoint --endpoint-name <name>.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious SageMaker behaviors

These behaviors change classification if ignored. Each is easy to misjudge
without operational SageMaker experience.

- **VpcConfig lives on the Model, NOT the EndpointConfig.** This is the single
  most common audit error. An EndpointConfig without VPC fields does NOT mean
  the endpoint is public — the Model's `VpcConfig` determines network
  placement. Always check `aws sagemaker describe-model`, not just
  `describe-endpoint-config`.

- **EnableNetworkIsolation and VpcConfig are independent controls.** A Model
  can have `VpcConfig` set with `EnableNetworkIsolation: false` (container can
  egress via VPC NAT), `VpcConfig` with `EnableNetworkIsolation: true` (fully
  locked down), or no `VpcConfig` with `EnableNetworkIsolation: false` (direct
  internet access — the most exposed posture). A Model with no VpcConfig but
  `EnableNetworkIsolation: true` still runs on AWS-managed VPC infrastructure
  but cannot make outbound calls — the endpoint API is still internet-reachable
  for invocation. **The PUBLIC_ENDPOINT verdict is driven by VpcConfig
  absence, not by EnableNetworkIsolation.**

- **EnableInterContainerTrafficEncryption only matters for inference
  pipelines.** A single-container endpoint has no inter-container traffic —
  the flag is a harmless no-op. Do NOT flag it as a missing control on a
  single-container endpoint. For a SerialInferencePipeline (multiple containers
  chained), inter-container encryption prevents plaintext traffic between
  containers on the same instance.

- **SageMaker InvokeEndpoint uses TLS by default.** Client-to-endpoint traffic
  is always encrypted in transit via the SageMaker API HTTPS endpoint. There
  is no "disable TLS" option. The encryption finding is about data-at-rest
  (KmsKeyId) and inter-container pipeline traffic — NOT about the invocation
  transport.

- **The execution role is on the Model, not the EndpointConfig.** Auditors who
  scan only the EndpointConfig for a role ARN will miss it entirely. The
  `ExecutionRoleArn` on the Model is the identity the container assumes at
  runtime — it determines what S3 buckets, KMS keys, and other AWS resources
  the model code can access.

- **DataCaptureConfig is a prerequisite for Model Monitor.** Without
  `EnableCapture: true`, the monitoring schedule has no data to analyze. But
  data capture alone is not monitoring — you also need a MonitoringSchedule.
  A common false positive is flagging "no monitoring" when DataCaptureConfig
  is enabled but no schedule exists.

- **InitialSamplingPercentage: 0 is effectively no capture.** DataCaptureConfig
  with `EnableCapture: true` but `InitialSamplingPercentage: 0` captures zero
  requests. Treat as NO_MONITORING — the operator may believe capture is active
  when it is not.

- **InitialInstanceCount vs CurrentInstanceCount.** The EndpointConfig declares
  `InitialInstanceCount`, but a SageMaker auto-scaling policy can change the
  actual count at runtime. For HA auditing, check `CurrentInstanceCount` on
  `DescribeEndpoint` `ProductionVariants` if available; otherwise fall back to
  `InitialInstanceCount`.

- **Serverless endpoints have no instance count.** `ProductionVariants` on a
  serverless endpoint uses `ServerlessConfig` (memory + max concurrency), not
  `InitialInstanceCount`. Skip the instance-count HA check for serverless.

- **Async endpoints can scale to zero.** An async endpoint with
  `InitialInstanceCount: 1` is a valid cost-optimisation pattern (scale to zero
  when idle). Flag single-instance async endpoints as CONFIG_GAP only if the
  endpoint serves production traffic with latency requirements.

- **SageMaker Model Monitor covers four monitoring types.** DataQuality,
  ModelQuality, BiasDrift, ExplainabilityDrift. Any one counts as "monitoring
  enabled" for the NO_MONITORING verdict, but note which types are missing in
  FINDINGS.

- **Model Monitor vs SageMaker Clarify.** Clarify handles pre-training bias
  detection and explainability (a build-time tool). Model Monitor handles
  runtime drift detection (a deploy-time tool). Do not confuse Clarify
  enablement with monitoring coverage.

- **Async OutputConfig S3 path.** For async endpoints, the
  `AsyncInferenceConfig.OutputConfig.S3OutputPath` stores inference results.
  If the destination S3 bucket lacks SSE-KMS encryption, async inference
  outputs are unencrypted at rest. Flag as a NO_ENCRYPTION additive finding.

### Step 1: VPC configuration — PUBLIC_ENDPOINT (highest severity)

If the Model has no `VpcConfig` (absent or empty), the endpoint is deployed on
AWS-managed public infrastructure — **the invocation API is internet-facing**.
Any client with the endpoint URL and valid AWS credentials can invoke the
model. This is the most exposed posture.

```text
VERDICT: PUBLIC_ENDPOINT
REASON: Model has no VpcConfig — endpoint is deployed on internet-facing
infrastructure. The InvokeEndpoint API is reachable from any network.
```

**Security-group refinement:** if `VpcConfig` IS present, inspect the
`SecurityGroupIds`. A security group with an inbound rule allowing `0.0.0.0/0`
on any port makes the endpoint effectively public within the VPC. Flag as
PUBLIC_ENDPOINT.

**EnableNetworkIsolation note:** a Model with no `VpcConfig` but
`EnableNetworkIsolation: true` prevents the container from making outbound
calls, but the endpoint API is STILL internet-reachable for invocation. The
PUBLIC_ENDPOINT verdict stands — network isolation restricts egress, not
ingress to the endpoint API.

### Step 2: Encryption — NO_ENCRYPTION

Evaluate two encryption dimensions:

**2a. KMS encryption at rest.** Check `KmsKeyId` on the EndpointConfig. If
absent, the EBS volumes attached to the endpoint instances and the model
artifact storage are unencrypted at rest. A compromised instance or snapshot
exposes model weights and artifacts.

- No `KmsKeyId` on EndpointConfig → **NO_ENCRYPTION**.

**2b. Inter-container traffic encryption (inference pipelines only).** If the
Model has multiple containers (a `SerialInferencePipeline` — check
`Containers` array length > 1 or `PrimaryContainer` + the inference pipeline
config), check `EnableInterContainerTrafficEncryption` on the EndpointConfig.

- Multi-container endpoint + `EnableInterContainerTrafficEncryption: false`
  → **NO_ENCRYPTION** (plaintext traffic between containers on the same host).
- Single-container endpoint → this flag is a no-op. Do NOT flag.

**2c. Async output S3 encryption (additive).** For async endpoints, if
`AsyncInferenceConfig.OutputConfig.S3OutputPath` points to an S3 bucket
without SSE-KMS encryption, append an additive NO_ENCRYPTION finding.

### Step 3: Execution role blast radius — OVERPERMISSIVE_ROLE

Evaluate the Model's `ExecutionRoleArn` trust policy (the identity-based
policy attached to the role). The execution role determines what AWS resources
the model container can access at runtime. Apply the same classification as
the iam-least-privilege-advisor:

- `Action: "*"` on `Resource: "*"` → **OVERPERMISSIVE_ROLE** (admin-equivalent
  — the container can do anything in the account).
- Service wildcard on `"*"` (`sagemaker:*`, `s3:*`, `iam:*`, `kms:*`,
  `secretsmanager:*`) → **OVERPERMISSIVE_ROLE**. The execution role only needs
  narrow permissions (InvokeEndpoint, S3 GetObject on model artifacts, KMS
  Decrypt on the endpoint key). Service wildcards are always over-scoped.
- `iam:PassRole` on `"*"` → **OVERPERMISSIVE_ROLE** (privilege escalation —
  the container can pass any role to any service).
- `NotAction` / `NotResource` → **OVERPERMISSIVE_ROLE** (inverse wildcards).
- Named actions on specific ARNs → pass this step.

**The SageMaker execution-role minimum-viable permission set:**
`sagemaker:InvokeEndpoint` (self), `s3:GetObject` on the model artifact
bucket/prefix, `kms:Decrypt` on the endpoint KMS key, and optionally
`logs:CreateLogStream` / `logs:PutLogEvents` on the CloudWatch log group.
Anything beyond this scope should be justified by the model's runtime
behaviour (e.g., calling a downstream API, reading a feature store).

If no execution-role policy document is provided, note:
"Execution-role policy not provided — cannot evaluate IAM blast radius.
Retrieve with `aws iam list-attached-role-policies --role-name <name>` and
`aws iam get-role-policy --role-name <name> --policy-name <name>`."

### Step 4: Monitoring coverage — NO_MONITORING

Evaluate two monitoring dimensions:

**4a. Data capture.** Check `DataCaptureConfig` on the EndpointConfig.

- No `DataCaptureConfig` → data capture is disabled.
- `EnableCapture: false` → data capture is disabled.
- `EnableCapture: true` but `InitialSamplingPercentage: 0` → effectively
  disabled (zero requests captured).

**4b. Monitoring schedule.** Check for a `MonitoringSchedule` referencing the
endpoint name.

- No monitoring schedule → no drift detection.
- Monitoring schedule with `Status: Stopped` → schedule exists but is inactive.

**Classification:**
- No data capture AND no monitoring schedule → **NO_MONITORING**.
- Data capture enabled but no monitoring schedule → **NO_MONITORING** (capture
  alone provides no alerts; the data sits idle without a schedule to analyse
  it).
- Monitoring schedule exists but data capture disabled → **NO_MONITORING**
  (the schedule has no data to analyse — Model Monitor cannot function without
  captured request/response payloads).
- Both data capture (with sampling > 0) AND an active monitoring schedule →
  pass this step.

### Step 5: Instance count / HA — CONFIG_GAP

Check `InitialInstanceCount` (or `CurrentInstanceCount` if available) on the
endpoint's `ProductionVariants`.

- `InitialInstanceCount < 2` → **CONFIG_GAP** (single instance — no high
  availability. If the instance fails, the endpoint goes down with no
  fallback. Production endpoints should have at least 2 instances across
  different Availability Zones).
- Serverless endpoint → skip this step (scale-to-zero by design).
- Async endpoint with `InitialInstanceCount: 1` → note as CONFIG_GAP but
  acknowledge the cost-optimisation trade-off (async endpoints can scale to
  zero; flag only if the endpoint serves latency-sensitive production
  traffic).

### Step 6: All dimensions pass — OK

If all of the following hold:
- Model has `VpcConfig` with restrictive security groups.
- EndpointConfig has `KmsKeyId`.
- (Multi-container endpoints have `EnableInterContainerTrafficEncryption: true`).
- Execution role has named actions on specific ARNs (no wildcards).
- Data capture is enabled with sampling > 0 AND an active monitoring schedule
  exists.
- `InitialInstanceCount >= 2` (or serverless/async with justification).

→ **VERDICT: OK**

### Step 7: Aggregation

The final verdict is the **worst finding** across all steps, where:
PUBLIC_ENDPOINT > NO_ENCRYPTION > OVERPERMISSIVE_ROLE > NO_MONITORING > CONFIG_GAP > OK

All individual findings are listed in the FINDINGS section regardless of the
aggregate verdict.

## Output format (per endpoint)

```text
ENDPOINT: <endpoint-name>
VERDICT: PUBLIC_ENDPOINT | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | NO_MONITORING | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [PUBLIC_ENDPOINT] <finding description (Step N)>
  - [NO_MONITORING] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific CLI action per finding, or "None required" if OK>
```

### Worked example — public endpoint with no monitoring

```text
ENDPOINT: public-endpoint-no-vpc
VERDICT: PUBLIC_ENDPOINT
REASON: Model has no VpcConfig — the endpoint is deployed on internet-facing
infrastructure (Step 1). Data capture is also disabled with no monitoring
schedule (Step 4).
FINDINGS:
  - [PUBLIC_ENDPOINT] No VpcConfig on Model — InvokeEndpoint API reachable
    from any network (Step 1)
  - [NO_MONITORING] No DataCaptureConfig and no MonitoringSchedule — drift
    undetectable (Step 4)
  - [OK] KmsKeyId present on EndpointConfig (Step 2)
  - [OK] Execution role scoped to named actions (Step 3)
REMEDIATION:
  1. Attach a VpcConfig to the Model:
     aws sagemaker create-model --model-name <name> --containers <spec>
       --vpc-config Subnets=<subnet-ids>,SecurityGroupIds=<sg-ids>
  2. Enable data capture on the EndpointConfig and create a monitoring
     schedule (see Remediation guidance below).
```

## Anti-Patterns — NEVER

- NEVER conclude an endpoint is "private" or "VPC-attached" by checking only
  the EndpointConfig. `VpcConfig` lives on the **Model** — the EndpointConfig
  has no VPC fields. Checking the wrong object is the most common false
  negative in SageMaker endpoint audits.

- NEVER flag `EnableInterContainerTrafficEncryption: false` on a
  **single-container** endpoint. There is no inter-container traffic to
  encrypt. The flag is a no-op. Flagging it is a false positive that erodes
  trust.

- NEVER classify an endpoint without `VpcConfig` but with
  `EnableNetworkIsolation: true` as "private." Network isolation blocks
  container **egress**; it does not prevent inbound invocation. The
  InvokeEndpoint API is still internet-reachable. The verdict is
  PUBLIC_ENDPOINT.

- NEVER assume the execution role is on the EndpointConfig or Endpoint. It is
  on the **Model** (`ExecutionRoleArn`). Scanning the wrong object yields no
  role and a silent pass on the IAM dimension.

- NEVER treat `EnableCapture: true` as "monitoring enabled." Data capture
  stores request/response payloads to S3 — it provides no alerts. A
  MonitoringSchedule is required to analyse the captured data and emit drift
  findings. Both must be present.

- NEVER accept `InitialSamplingPercentage: 0` as valid data capture. Zero
  percent sampling captures zero requests. The operator may believe monitoring
  is active when it is silently inert.

- NEVER flag a serverless endpoint for `InitialInstanceCount` being absent or
  below 2. Serverless endpoints use `ServerlessConfig` (memory size + max
  concurrency), not instance count. The HA dimension does not apply.

- NEVER assume `EndpointStatus: Failed` means the endpoint has no security
  findings. A failed deployment often fails BECAUSE of a security
  misconfiguration (e.g., execution role missing `sagemaker:CreateModel`,
  VPC lacking S3 VPC endpoint for model artifacts). Audit the config — the
  security finding may explain the failure.

- NEVER recommend `sagemaker:*` as a remediation for the execution role. The
  execution role needs `sagemaker:InvokeEndpoint` at most — `sagemaker:*`
  grants model/endpoint creation and deletion, which the container never
  needs at runtime. This reintroduces the exact blast radius being constrained.

- NEVER overlook the async OutputConfig S3 path for async endpoints. Async
  inference outputs are written to the configured S3 path. If the bucket
  lacks SSE-KMS, outputs are unencrypted at rest — a silent data-exposure gap.

- NEVER treat SageMaker Clarify enablement as a substitute for Model Monitor.
  Clarify runs at build time (pre-training bias, explainability baselines).
  Model Monitor runs at inference time (runtime drift detection). They are
  different services with different triggers.

- NEVER conflate `InitialInstanceCount` (EndpointConfig) with
  `CurrentInstanceCount` (DescribeEndpoint runtime). Auto-scaling can change
  the count after deployment. For HA auditing, prefer the runtime value when
  available.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (CreateModel, UpdateEndpoint, UpdateEndpointConfig,
  UpdateEndpointWeightsAndCapacities, CreateMonitoringSchedule), emit:
  `CONFIRM: About to <action> on endpoint <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`. Do NOT execute until confirmed.
- **Updating a Model requires a new model version.** SageMaker Models are
  immutable — `VpcConfig` cannot be patched in place. To add a VpcConfig,
  you must `CreateModel` with the new config, then `UpdateEndpoint` pointing
  to a new EndpointConfig that references the new model. This is a multi-step
  operation with a brief endpoint downtime window.
- **DataCaptureConfig changes require a new EndpointConfig.** Like Models,
  EndpointConfigs are immutable. To enable data capture, create a new
  EndpointConfig with `DataCaptureConfig`, then `UpdateEndpoint` to the new
  config. The endpoint rolls through a blue/green deployment.
- **Snapshot the current configuration for rollback:**
  `aws sagemaker describe-endpoint --endpoint-name <name> --output json > /tmp/<name>-endpoint-backup-$(date +%s).json`
  BEFORE any modification. Endpoint configs are not versioned — there is no
  undo without a backup.
- **Verify the caller's identity can run the remediation commands.** Most
  read-only auditor roles CANNOT `UpdateEndpoint` or `CreateModel`. Surface
  this before the operator approves the change.
- **For VpcConfig remediation**, verify the target VPC has the required
  endpoints (S3, ECR, SageMaker APIs) or a NAT gateway — otherwise the
  endpoint deployment will fail because the container cannot pull the image
  or download model artifacts.

## Remediation guidance

### For PUBLIC_ENDPOINT — no VpcConfig

1. Create a new Model version with VpcConfig:
   ```bash
   aws sagemaker create-model --model-name <name>-vpc \
     --execution-role-arn <role-arn> --primary-container <container-spec> \
     --vpc-config Subnets=subnet-abc,subnet-def,SecurityGroupIds=sg-xyz \
     --enable-network-isolation
   ```
2. Create a new EndpointConfig referencing the new model.
3. Update the endpoint (blue/green):
   ```bash
   aws sagemaker update-endpoint --endpoint-name <name> \
     --endpoint-config-name <new-config>
   ```
4. Verify the endpoint is now VPC-attached:
   ```bash
   aws sagemaker describe-model --model-name <name>-vpc --query 'VpcConfig'
   ```

### For NO_ENCRYPTION — no KMS key

1. Create a new EndpointConfig with a customer-managed KMS key:
   ```bash
   aws sagemaker create-endpoint-config --endpoint-config-name <name>-enc \
     --production-variants <variants> \
     --kms-key-id arn:aws:kms:us-east-1:<acct>:key/<key-id>
   ```
2. For inference pipelines, add
   `--enable-inter-container-traffic-encryption`.
3. Update the endpoint to the new config.
4. For async endpoints, ensure the OutputConfig S3 bucket has SSE-KMS enabled.

### For OVERPERMISSIVE_ROLE — wildcard execution role

1. Replace wildcard actions with the minimum-viable permission set:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": [
         "sagemaker:InvokeEndpoint",
         "s3:GetObject"
       ],
       "Resource": [
         "arn:aws:sagemaker:us-east-1:<acct>:endpoint/<name>",
         "arn:aws:s3:::<model-bucket>/<prefix>/*"
       ]
     }]
   }
   ```
2. Add KMS decrypt scoped to the endpoint key if the endpoint uses SSE-KMS.
3. Derive the exact action set from CloudTrail (90-day window of
   `userIdentity.arn` matching the execution role).

### For NO_MONITORING — no data capture or schedule

1. Create a new EndpointConfig with DataCaptureConfig:
   ```bash
   aws sagemaker create-endpoint-config --endpoint-config-name <name>-cap \
     --production-variants <variants> \
     --data-capture-config EnableCapture=true,InitialSamplingPercentage=100,DestinationS3Uri=s3://<bucket>/capture/,CaptureOptions=[{CaptureMode=Input},{CaptureMode=Output}]
   ```
2. Update the endpoint to the new config.
3. Create a monitoring schedule:
   ```bash
   aws sagemaker create-monitoring-schedule \
     --monitoring-schedule-name <name>-dq-monitor \
     --endpoint-name <name> \
     --monitoring-type DataQuality \
     --monitoring-job-definition <job-def>
   ```

### For CONFIG_GAP — single instance

1. Update the endpoint weights and capacities:
   ```bash
   aws sagemaker update-endpoint-weights-and-capacities \
     --endpoint-name <name> \
     --desired-weights-and-capacities variantName=<variant>,DesiredInstanceCount=2
   ```
2. For async endpoints with justified scale-to-zero, document the
   cost-optimisation trade-off and suppress the finding.

### For OK

1. No remediation required.
2. Recommend verifying the monitoring schedule is producing results:
   `aws sagemaker describe-monitoring-schedule --monitoring-schedule-name <name>`.
3. Recommend reviewing captured data quarterly to confirm sampling is
  representative.

## Recent AWS features (2024-2026)

- **Inference Components (2024):** SageMaker Inference Components allow deploying multiple models on a single endpoint with independent scaling. Auditors should verify that each model within an inference component has appropriate IAM permissions and that the container image is scanned for vulnerabilities.
- **Zero-downtime endpoint updates (2024):** SageMaker now supports zero-downtime blue/green endpoint updates. Auditors should verify that production endpoints use rolling or blue/green update strategies rather than the default replace strategy.
- **SageMaker HyperPod (2024-2025):** HyperPod provides managed distributed training clusters. Auditors should verify that HyperPod instances have encrypted EBS volumes, scoped execution roles, and appropriate VPC configuration.
- **SageMaker Unified Studio (2025):** Unified Studio integrates SageMaker Studio, EMR, and data governance. Auditors should verify that Unified Studio's IAM domain roles are scoped appropriately and that data access is governed by Lake Formation.
- **EKS-based SageMaker inference (2024):** SageMaker can now run inference workloads on EKS clusters. Auditors should verify that the EKS-based inference uses appropriate pod-level IAM and security policies.

## Domain

AWS CloudOps / SageMaker AI/ML Security & Production Readiness.
