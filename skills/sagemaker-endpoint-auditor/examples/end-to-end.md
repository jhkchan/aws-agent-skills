# End-to-end usage scenario: sagemaker-endpoint-auditor

A walkthrough showing the skill auditing a SageMaker endpoint that has both
a public exposure (PUBLIC_ENDPOINT — no VpcConfig on the Model) and a
monitoring gap (NO_MONITORING), demonstrating precedence aggregation, the
VpcConfig-on-Model knowledge delta, and the blue/green remediation workflow.

## Input (user prompt)

> Review this SageMaker endpoint before we promote it to production. It
> serves our fraud-detection model for real-time transaction scoring.

```text
Endpoint name: fraud-detection-prod
Endpoint metadata:
  EndpointStatus: InService
  EndpointType: real-time

Model (describe-model):
  ModelName: fraud-detection-prod-model
  ExecutionRoleArn: arn:aws:iam::111111111111:role/sagemaker-fraud-role
  EnableNetworkIsolation: false
  VpcConfig: (absent)
  PrimaryContainer:
    Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-cpu
    ModelDataUrl: s3://fraud-models-111111111111/fraud-detection-v3/model.tar.gz

EndpointConfig (describe-endpoint-config):
  EndpointConfigName: fraud-detection-prod-config
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/fraud-enc-key
  EnableInterContainerTrafficEncryption: true
  ProductionVariants:
    - InstanceType: ml.c5.xlarge
      InitialInstanceCount: 2
  DataCaptureConfig: (absent)

MonitoringSchedule: (none)

Execution role policy (attached to sagemaker-fraud-role):
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sagemaker:InvokeEndpoint"],
      "Resource": "arn:aws:sagemaker:us-east-1:111111111111:endpoint/fraud-detection-prod"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::fraud-models-111111111111/*"
    }
  ]
}
```

## Skill output

```text
ENDPOINT: fraud-detection-prod
VERDICT: PUBLIC_ENDPOINT
REASON: Model has no VpcConfig — the endpoint is deployed on internet-facing
infrastructure and the InvokeEndpoint API is reachable from any network
(Step 1). Data capture is also absent with no monitoring schedule (Step 4).
FINDINGS:
  - [PUBLIC_ENDPOINT] No VpcConfig on Model fraud-detection-prod-model —
    endpoint is internet-facing; any client with valid AWS credentials can
    invoke the fraud-detection model (Step 1)
  - [NO_MONITORING] No DataCaptureConfig on EndpointConfig and no
    MonitoringSchedule — data drift and model quality degradation are
    undetectable (Step 4)
  - [OK] KmsKeyId present: arn:aws:kms:us-east-1:111111111111:key/fraud-enc-key (Step 2)
  - [OK] Execution role scoped to sagemaker:InvokeEndpoint + s3:GetObject on
    specific ARNs (Step 3)
  - [OK] InitialInstanceCount: 2 — multi-AZ high availability (Step 5)
REMEDIATION:
  1. PUBLIC_ENDPOINT — Create a new Model version with VpcConfig (Models are
     immutable — VpcConfig cannot be patched in place):
     aws sagemaker create-model --model-name fraud-detection-prod-model-vpc \
       --execution-role-arn arn:aws:iam::111111111111:role/sagemaker-fraud-role \
       --primary-container <container-spec> \
       --vpc-config Subnets=subnet-abc,subnet-def,SecurityGroupIds=sg-xyz \
       --enable-network-isolation
  2. Create a new EndpointConfig referencing the new model AND with
     DataCaptureConfig enabled:
     aws sagemaker create-endpoint-config --endpoint-config-name fraud-detection-prod-config-v2 \
       --production-variants <variants> \
       --kms-key-id arn:aws:kms:us-east-1:111111111111:key/fraud-enc-key \
       --data-capture-config EnableCapture=true,InitialSamplingPercentage=100,DestinationS3Uri=s3://fraud-capture-111111111111/fraud-detection-prod/,CaptureOptions=[{CaptureMode=Input},{CaptureMode=Output}]
  3. Update the endpoint (blue/green deployment):
     aws sagemaker update-endpoint --endpoint-name fraud-detection-prod \
       --endpoint-config-name fraud-detection-prod-config-v2
  4. Create a monitoring schedule:
     aws sagemaker create-monitoring-schedule \
       --monitoring-schedule-name fraud-detection-prod-dq \
       --endpoint-name fraud-detection-prod \
       --monitoring-type DataQuality \
       --monitoring-job-definition <job-def>
```

## What the skill caught that a generic assistant misses

1. **VpcConfig lives on the Model, not the EndpointConfig.** A generic
   assistant scans the EndpointConfig for VPC settings, finds none, and
   either skips the network dimension or incorrectly reports the endpoint
   as VPC-attached. The skill knows VpcConfig is on the Model — the
   EndpointConfig has no VPC fields at all.

2. **The precedence is PUBLIC_ENDPOINT, not NO_MONITORING.** Both findings
   are present, but the verdict is PUBLIC_ENDPOINT because internet exposure
   is a higher-severity finding than a monitoring gap. The FINDINGS list
   shows both so the operator can triage independently.

3. **EnableNetworkIsolation: false without VpcConfig is the worst posture.**
   The skill recognises that no VpcConfig + no network isolation means the
   container has direct internet access — it can exfiltrate data, call
   external APIs, or download payloads. This compounds the PUBLIC_ENDPOINT
   finding.

4. **The remediation is a multi-step blue/green workflow, not a one-liner.**
   SageMaker Models and EndpointConfigs are immutable — you cannot patch
   VpcConfig or DataCaptureConfig in place. The skill's remediation
   creates a new Model version, a new EndpointConfig, and triggers a
   blue/green UpdateEndpoint — the only safe path.

## Slash-command invocation

```
/aws:audit-sagemaker-endpoint
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this SageMaker endpoint before production promotion"
```

The orchestrator emits
`[Phase: Audit | Skills routed: sagemaker-endpoint-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this SageMaker endpoint"
# [Phase: Audit | Skills routed: sagemaker-endpoint-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the endpoint, validate the posture:

```bash
# Verify the new model has VpcConfig
aws sagemaker describe-model --model-name fraud-detection-prod-model-vpc \
  --profile default --query 'VpcConfig'

# Confirm data capture is enabled on the new config
aws sagemaker describe-endpoint-config \
  --endpoint-config-name fraud-detection-prod-config-v2 \
  --profile default --query 'DataCaptureConfig'

# Check the monitoring schedule is producing results
aws sagemaker describe-monitoring-schedule \
  --monitoring-schedule-name fraud-detection-prod-dq \
  --profile default

# Verify the endpoint is InService after the blue/green update
aws sagemaker describe-endpoint --endpoint-name fraud-detection-prod \
  --profile default --query 'EndpointStatus'
```

Then monitor CloudTrail for `sagemaker:InvokeEndpoint` calls from unexpected
sources for 1-2 weeks to confirm the VPC placement is effective.
