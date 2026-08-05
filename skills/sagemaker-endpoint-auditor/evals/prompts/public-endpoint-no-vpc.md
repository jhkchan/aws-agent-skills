# Eval prompt: public-endpoint-no-vpc

Audit the following SageMaker endpoint configuration for security posture and
production readiness. Emit the standard VERDICT block (ENDPOINT, VERDICT,
REASON, FINDINGS, REMEDIATION).

Endpoint name: public-endpoint-no-vpc
Endpoint metadata:
  EndpointStatus: InService
  EndpointType: real-time

Model (describe-model):
  ModelName: public-endpoint-no-vpc-model
  ExecutionRoleArn: arn:aws:iam::111111111111:role/sagemaker-scoped-invoke-role
  EnableNetworkIsolation: false
  VpcConfig: (absent)
  PrimaryContainer:
    Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1-cpu
    ModelDataUrl: s3://model-artifacts-111111111111/public-endpoint-no-vpc/model.tar.gz

EndpointConfig (describe-endpoint-config):
  EndpointConfigName: public-endpoint-no-vpc-config
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/abc-encrypted-key
  EnableInterContainerTrafficEncryption: true
  ProductionVariants:
    - InstanceType: ml.m5.xlarge
      InitialInstanceCount: 2
  DataCaptureConfig:
    EnableCapture: true
    InitialSamplingPercentage: 100
    DestinationS3Uri: s3://capture-bucket-111111111111/public-endpoint-no-vpc/
    CaptureOptions:
      - CaptureMode: Input
      - CaptureMode: Output

MonitoringSchedule:
  MonitoringScheduleName: public-endpoint-no-vpc-dq
  EndpointName: public-endpoint-no-vpc
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
      "Resource": "arn:aws:sagemaker:us-east-1:111111111111:endpoint/public-endpoint-no-vpc"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::model-artifacts-111111111111/*"
    }
  ]
}
```
