# SageMaker Endpoint Auditor — Advanced Patterns

Step-0 non-obvious SageMaker behaviors and recent AWS features, moved verbatim from SKILL.md for progressive disclosure.

## Step 0: Expert knowledge — non-obvious SageMaker behaviors

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

## Recent AWS features (2024-2026)

- **Inference Components (2024):** SageMaker Inference Components allow deploying multiple models on a single endpoint with independent scaling. Auditors should verify that each model within an inference component has appropriate IAM permissions and that the container image is scanned for vulnerabilities.
- **Zero-downtime endpoint updates (2024):** SageMaker now supports zero-downtime blue/green endpoint updates. Auditors should verify that production endpoints use rolling or blue/green update strategies rather than the default replace strategy.
- **SageMaker HyperPod (2024-2025):** HyperPod provides managed distributed training clusters. Auditors should verify that HyperPod instances have encrypted EBS volumes, scoped execution roles, and appropriate VPC configuration.
- **SageMaker Unified Studio (2025):** Unified Studio integrates SageMaker Studio, EMR, and data governance. Auditors should verify that Unified Studio's IAM domain roles are scoped appropriately and that data access is governed by Lake Formation.
- **EKS-based SageMaker inference (2024):** SageMaker can now run inference workloads on EKS clusters. Auditors should verify that the EKS-based inference uses appropriate pod-level IAM and security policies.

