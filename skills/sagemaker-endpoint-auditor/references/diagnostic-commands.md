# SageMaker Endpoint Auditor — Diagnostic and Pre-flight Commands

Pre-flight safety checks and rollback commands run before any remediation CLI, moved verbatim from SKILL.md.

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

