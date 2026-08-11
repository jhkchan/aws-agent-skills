# Eval: real-time-endpoint-production

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, real-time endpoint with 2-instance HA, auto-scaling, data capture, model monitor

## Prompt

Deploy a SageMaker real-time inference endpoint in us-east-1 for a
recommendation model. Endpoint name "prod-recommendation". Model
artifact at s3://ml-artifacts/models/rec/model.tar.gz. Container image
763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310.
Execution role arn:aws:iam::123456789012:role/SageMakerExecutionRole.
Instance type ml.c5.xlarge, initial count 2 for HA. Auto-scaling on
InvocationsPerInstance with target 14, min 2, max 8. Data capture
enabled at 20% sampling to s3://sagemaker-captures-prod/rec/.
Data quality model monitor on hourly schedule. KMS encryption with
key alias/prod-sagemaker-key. VPC subnets subnet-aaa, subnet-bbb,
security group sg-xxx. Tags: Environment=production, Workload=recommendation.
Account ID: 123456789012.
