# Eval prompt: config-gap-single-instance

Audit the following SageMaker endpoint configuration for security posture and
production readiness. Emit the standard VERDICT block (ENDPOINT, VERDICT,
REASON, FINDINGS, REMEDIATION).

Endpoint name: config-gap-single-instance
Endpoint metadata:
  EndpointStatus: InService
  EndpointType: real-time

Model (describe-model):
  ModelName: config-gap-single-instance-model
  ExecutionRoleArn: arn:aws:iam::111111111111:role/sagemaker-scoped-invoke-role
  EnableNetworkIsolation: true
  VpcConfig:
    Subnets: [subnet-abc123, subnet-def456]
    SecurityGroupIds: [sg-locked-down-001]
  PrimaryContainer:
    Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1-cpu
    ModelDataUrl: s3://model-artifacts-111111111111/config-gap-single-instance/model.tar.gz

EndpointConfig (describe-endpoint-config):
  EndpointConfigName: config-gap-single-instance-config
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/ha-key-777
  EnableInterContainerTrafficEncryption: true
  ProductionVariants:
    - InstanceType: ml.m5.xlarge
      InitialInstanceCount: 1
  DataCaptureConfig:
    EnableCapture: true
    InitialSamplingPercentage: 100
    DestinationS3Uri: s3://capture-bucket-111111111111/config-gap-single-instance/
    CaptureOptions:
      - CaptureMode: Input
      - CaptureMode: Output

MonitoringSchedule:
  MonitoringScheduleName: config-gap-single-instance-dq
  EndpointName: config-gap-single-instance
  MonitoringType: DataQuality
  Status: Scheduled

Execution role policy (attached to sagemaker-scoped-invoke-role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sagemaker:InvokeEndpoint"],
      "Resource": "arn:aws:sagemaker:us-east-1:111111111111:endpoint/config-gap-single-instance"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::model-artifacts-111111111111/*"
    }
  ]
}
```
