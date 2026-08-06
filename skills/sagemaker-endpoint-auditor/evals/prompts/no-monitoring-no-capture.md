# Eval prompt: no-monitoring-no-capture

Audit the following SageMaker endpoint configuration for security posture and
production readiness. Emit the standard VERDICT block (ENDPOINT, VERDICT,
REASON, FINDINGS, REMEDIATION).

Endpoint name: no-monitoring-no-capture
Endpoint metadata:
  EndpointStatus: InService
  EndpointType: real-time

Model (describe-model):
  ModelName: no-monitoring-no-capture-model
  ExecutionRoleArn: arn:aws:iam::111111111111:role/sagemaker-scoped-invoke-role
  EnableNetworkIsolation: true
  VpcConfig:
    Subnets: [subnet-abc123, subnet-def456]
    SecurityGroupIds: [sg-locked-down-001]
  PrimaryContainer:
    Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1-cpu
    ModelDataUrl: s3://model-artifacts-111111111111/no-monitoring-no-capture/model.tar.gz

EndpointConfig (describe-endpoint-config):
  EndpointConfigName: no-monitoring-no-capture-config
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/mon-key-555
  EnableInterContainerTrafficEncryption: true
  ProductionVariants:
    - InstanceType: ml.m5.xlarge
      InitialInstanceCount: 2
  DataCaptureConfig: (absent)

MonitoringSchedule: (none)

Execution role policy (attached to sagemaker-scoped-invoke-role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sagemaker:InvokeEndpoint"],
      "Resource": "arn:aws:sagemaker:us-east-1:111111111111:endpoint/no-monitoring-no-capture"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::model-artifacts-111111111111/*"
    }
  ]
}
```
