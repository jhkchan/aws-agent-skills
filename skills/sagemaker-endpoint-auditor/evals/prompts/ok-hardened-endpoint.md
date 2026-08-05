# Eval prompt: ok-hardened-endpoint

Audit the following SageMaker endpoint configuration for security posture and
production readiness. Emit the standard VERDICT block (ENDPOINT, VERDICT,
REASON, FINDINGS, REMEDIATION).

Endpoint name: ok-hardened-endpoint
Endpoint metadata:
  EndpointStatus: InService
  EndpointType: real-time

Model (describe-model):
  ModelName: ok-hardened-endpoint-model
  ExecutionRoleArn: arn:aws:iam::111111111111:role/sagemaker-scoped-invoke-role
  EnableNetworkIsolation: true
  VpcConfig:
    Subnets: [subnet-abc123, subnet-def456]
    SecurityGroupIds: [sg-locked-down-001]
  PrimaryContainer:
    Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1-cpu
    ModelDataUrl: s3://model-artifacts-111111111111/ok-hardened-endpoint/model.tar.gz

EndpointConfig (describe-endpoint-config):
  EndpointConfigName: ok-hardened-endpoint-config
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/hardened-key-ok
  EnableInterContainerTrafficEncryption: true
  ProductionVariants:
    - InstanceType: ml.m5.xlarge
      InitialInstanceCount: 2
  DataCaptureConfig:
    EnableCapture: true
    InitialSamplingPercentage: 100
    DestinationS3Uri: s3://capture-bucket-111111111111/ok-hardened-endpoint/
    CaptureOptions:
      - CaptureMode: Input
      - CaptureMode: Output

MonitoringSchedule:
  MonitoringScheduleName: ok-hardened-endpoint-dq
  EndpointName: ok-hardened-endpoint
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
      "Resource": "arn:aws:sagemaker:us-east-1:111111111111:endpoint/ok-hardened-endpoint"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::model-artifacts-111111111111/*"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/hardened-key-ok"
    }
  ]
}
```
