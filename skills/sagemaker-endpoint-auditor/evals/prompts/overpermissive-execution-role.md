# Eval prompt: overpermissive-execution-role

Audit the following SageMaker endpoint configuration for security posture and
production readiness. Emit the standard VERDICT block (ENDPOINT, VERDICT,
REASON, FINDINGS, REMEDIATION).

Endpoint name: overpermissive-execution-role
Endpoint metadata:
  EndpointStatus: InService
  EndpointType: real-time

Model (describe-model):
  ModelName: overpermissive-execution-role-model
  ExecutionRoleArn: arn:aws:iam::111111111111:role/sagemaker-admin-role
  EnableNetworkIsolation: true
  VpcConfig:
    Subnets: [subnet-abc123, subnet-def456]
    SecurityGroupIds: [sg-locked-down-001]
  PrimaryContainer:
    Image: 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1-cpu
    ModelDataUrl: s3://model-artifacts-111111111111/overpermissive-execution-role/model.tar.gz

EndpointConfig (describe-endpoint-config):
  EndpointConfigName: overpermissive-execution-role-config
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/sec-key-999
  EnableInterContainerTrafficEncryption: true
  ProductionVariants:
    - InstanceType: ml.m5.xlarge
      InitialInstanceCount: 2
  DataCaptureConfig:
    EnableCapture: true
    InitialSamplingPercentage: 100
    DestinationS3Uri: s3://capture-bucket-111111111111/overpermissive-execution-role/

MonitoringSchedule:
  MonitoringScheduleName: overpermissive-execution-role-dq
  EndpointName: overpermissive-execution-role
  MonitoringType: DataQuality
  Status: Scheduled

Execution role policy (attached to sagemaker-admin-role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```
