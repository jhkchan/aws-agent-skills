# Eval prompt: no-kms-encryption

Audit the following SageMaker endpoint configuration for security posture and
production readiness. Emit the standard VERDICT block (ENDPOINT, VERDICT,
REASON, FINDINGS, REMEDIATION).

Endpoint name: no-kms-encryption
Endpoint metadata:
  EndpointStatus: InService
  EndpointType: real-time

Model (describe-model):
  ModelName: no-kms-encryption-model
  ExecutionRoleArn: arn:aws:iam::111111111111:role/sagemaker-scoped-invoke-role
  EnableNetworkIsolation: true
  VpcConfig:
    Subnets: [subnet-abc123, subnet-def456]
    SecurityGroupIds: [sg-locked-down-001]
  Containers:
    - Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/sklearn-inference:1.3-cpu
      ModelDataUrl: s3://model-artifacts-111111111111/no-kms-encryption/preprocess.tar.gz
    - Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-cpu
      ModelDataUrl: s3://model-artifacts-111111111111/no-kms-encryption/model.tar.gz

EndpointConfig (describe-endpoint-config):
  EndpointConfigName: no-kms-encryption-config
  KmsKeyId: (absent)
  EnableInterContainerTrafficEncryption: false
  ProductionVariants:
    - InstanceType: ml.c5.xlarge
      InitialInstanceCount: 2
  DataCaptureConfig:
    EnableCapture: true
    InitialSamplingPercentage: 50
    DestinationS3Uri: s3://capture-bucket-111111111111/no-kms-encryption/

MonitoringSchedule:
  MonitoringScheduleName: no-kms-encryption-dq
  EndpointName: no-kms-encryption
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
      "Resource": "arn:aws:sagemaker:us-east-1:111111111111:endpoint/no-kms-encryption"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::model-artifacts-111111111111/*"
    }
  ]
}
```
