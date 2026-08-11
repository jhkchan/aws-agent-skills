# Provisioning CLI Commands — SageMaker Endpoint Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<endpoint-name>`, `<config-name>`, `<model-name>`,
`<region>`, `<account-id>`, `<bucket>`, `<image-uri>`, `<role-arn>`,
`<key-id>`, `<subnet-ids>`, `<sg-ids>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm S3 model artifact exists
aws s3 ls s3://<bucket>/<prefix>/model.tar.gz

# Confirm container image exists (DLC or custom ECR)
aws ecr describe-images --repository-name <repo> --region <region> \
  --query 'imageDetails[*].imageTags' --output text

# Confirm execution role exists and has required permissions
aws iam get-role --role-name SageMakerExecutionRole --query 'Role.Arn' --output text

# Confirm KMS key exists and is enabled
aws kms describe-key --key-id alias/<sagemaker-alias> \
  --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text

# Confirm VPC subnets span at least 2 AZs (for HA)
aws ec2 describe-subnets --subnet-ids <subnet-aaa> <subnet-bbb> \
  --query 'Subnets[*].[SubnetId,AvailabilityZone]' --output text
```

## Step 1: Create the model

```bash
aws sagemaker create-model \
  --model-name <model-name> \
  --primary-container \
    Image=<image-uri>,ModelDataUrl=s3://<bucket>/<prefix>/model.tar.gz \
  --execution-role-arn arn:aws:iam::<account-id>:role/SageMakerExecutionRole \
  --vpc-config Subnets=<subnet-aaa>,<subnet-bbb>,SecurityGroupIds=<sg-xxx>
```

For JumpStart foundation models, the artifact and container are pre-built:

```bash
aws sagemaker create-model \
  --model-name jumpstart-llama-7b \
  --primary-container \
    Image=763104351884.dkr.ecr.<region>.amazonaws.com/djl-inference:0.23.0-deepspeed0.9.5-cu118,ModelDataUrl=s3://jumpstart-cache-prod-<region>/meta-llama/models/meta-llama-7b/ \
  --execution-role-arn arn:aws:iam::<account-id>:role/SageMakerExecutionRole
```

## Step 2: Create endpoint config — real-time

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name> \
  --production-variants \
    VariantName=AllTraffic,ModelName=<model-name>,InstanceType=ml.c5.xlarge,InitialInstanceCount=2,InitialVariantWeight=1 \
  --data-capture-config \
    EnableCapture=true,InitialSamplingPercentage=20,DestinationS3Uri=s3://<capture-bucket>/captures/,CaptureOptions=[{CaptureMode=Input},{CaptureMode=Output}],CaptureContentTypeHeaders={JsonContentTypes=[application/json]} \
  --kms-key-id arn:aws:kms:<region>:<account-id>:key/<key-id>
```

## Step 3: Create endpoint config — serverless

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-serverless \
  --serverless-config \
    ServerlessInferenceConfigName=AllTraffic,MaxConcurrency=10,MemorySizeInMB=2048,ProvisionedConcurrency=2
```

Serverless does NOT use ProductionVariants or instance types.

## Step 4: Create endpoint config — asynchronous

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-async \
  --production-variants \
    VariantName=AllTraffic,ModelName=<model-name>,InstanceType=ml.g5.xlarge,InitialInstanceCount=1 \
  --async-inference-config \
    OutputConfig=S3OutputPath=s3://<async-bucket>/output/,NotificationConfig=SuccessTopic=<topic-arn>,ErrorTopic=<error-topic-arn>,MaxConcurrentInvocationsPerInstance=4
```

## Step 5: Create the endpoint

```bash
aws sagemaker create-endpoint \
  --endpoint-name <endpoint-name> \
  --endpoint-config-name <config-name>

# Wait for InService (5-15 minutes)
aws sagemaker describe-endpoint --endpoint-name <endpoint-name> \
  --query 'EndpointStatus' --output text
```

## Step 6: Auto-scaling — real-time (InvocationsPerInstance)

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace sagemaker \
  --resource-id endpoint/<endpoint-name>/variant/<variant-name> \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --min-capacity 2 --max-capacity 8

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --policy-name <endpoint-name>-scaling \
  --service-namespace sagemaker \
  --resource-id endpoint/<endpoint-name>/variant/<variant-name> \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    TargetValue=14,PredefinedMetricSpecification={PredefinedMetricType=SageMakerVariantInvocationsPerInstance},ScaleInCooldown=300,ScaleOutCooldown=60
```

## Step 7: Auto-scaling — async (ApproximateBacklogSizePerInstance)

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace sagemaker \
  --resource-id endpoint/<endpoint-name>/variant/<variant-name> \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --min-capacity 0 --max-capacity 4

aws application-autoscaling put-scaling-policy \
  --policy-name <endpoint-name>-async-scaling \
  --service-namespace sagemaker \
  --resource-id endpoint/<endpoint-name>/variant/<variant-name> \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    TargetValue=5,CustomizedMetricSpecification={MetricName=ApproximateBacklogSizePerInstance,Namespace=AWS/SageMaker,Statistic=Average},ScaleInCooldown=600,ScaleOutCooldown=60
```

## Step 8: A/B testing (multiple variants)

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-ab \
  --production-variants \
    '[{"VariantName":"variantA","ModelName":"<model-a>","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":9},
      {"VariantName":"variantB","ModelName":"<model-b>","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":1}]'

# Shift traffic weights without downtime
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name <endpoint-name> \
  --desired-weights-and-capacities variantA=5,variantB=5
```

## Step 9: Shadow testing

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name <config-name>-shadow \
  --production-variants \
    '[{"VariantName":"prod","ModelName":"<model-prod>","InstanceType":"ml.c5.xlarge","InitialInstanceCount":2,"InitialVariantWeight":1}]' \
  --shadow-production-variants \
    '[{"VariantName":"shadow","ModelName":"<model-candidate>","InstanceType":"ml.c5.xlarge","InitialInstanceCount":1}]'
```

## Step 10: CloudWatch alarms (recommended)

```bash
# Invocation 4XX errors
aws cloudwatch put-metric-alarm \
  --alarm-name "<endpoint>-4xx-errors" \
  --namespace AWS/SageMaker \
  --metric-name Invocation4XXErrors \
  --dimensions Name=EndpointName,Value=<endpoint-name> \
  --statistic Sum --period 300 --threshold 10 \
  --comparison-operator GreaterThanThreshold --evaluation-periods 2 \
  --alarm-actions <sns-arn>

# Invocation 5XX errors
aws cloudwatch put-metric-alarm \
  --alarm-name "<endpoint>-5xx-errors" \
  --namespace AWS/SageMaker \
  --metric-name Invocation5XXErrors \
  --dimensions Name=EndpointName,Value=<endpoint-name> \
  --statistic Sum --period 300 --threshold 5 \
  --comparison-operator GreaterThanThreshold --evaluation-periods 1 \
  --alarm-actions <sns-arn>

# Model latency
aws cloudwatch put-metric-alarm \
  --alarm-name "<endpoint>-high-latency" \
  --namespace AWS/SageMaker \
  --metric-name ModelLatency \
  --dimensions Name=EndpointName,Value=<endpoint-name> \
  --statistic Average --period 300 --threshold 500000 \
  --unit Microseconds \
  --comparison-operator GreaterThanThreshold --evaluation-periods 3 \
  --alarm-actions <sns-arn>
```

## Verification

```bash
aws sagemaker describe-endpoint --endpoint-name <endpoint-name>
aws sagemaker describe-endpoint-config --endpoint-config-name <config-name>
aws sagemaker describe-model --model-name <model-name>
aws application-autoscaling describe-scaling-policies --service-namespace sagemaker
aws s3 ls s3://<capture-bucket>/captures/<endpoint-name>/AllTraffic/
```

## Terraform equivalent

```hcl
resource "aws_sagemaker_model" "model" {
  name               = "<model-name>"
  execution_role_arn = aws_iam_role.sagemaker.arn

  primary_container {
    image          = "<image-uri>"
    model_data_url = "s3://<bucket>/<prefix>/model.tar.gz"
  }

  vpc_config {
    security_group_ids = ["<sg-xxx>"]
    subnets            = ["<subnet-aaa>", "<subnet-bbb>"]
  }
}

resource "aws_sagemaker_endpoint_configuration" "config" {
  name        = "<config-name>"
  kms_key_arn = aws_kms_key.sagemaker.arn

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.model.name
    instance_type          = "ml.c5.xlarge"
    initial_instance_count = 2
    initial_variant_weight = 1
  }

  data_capture_config {
    enable_capture              = true
    initial_sampling_percentage = 20
    destination_s3_uri          = "s3://<capture-bucket>/captures/"

    capture_options {
      capture_mode = "Input"
    }
    capture_options {
      capture_mode = "Output"
    }
  }
}

resource "aws_sagemaker_endpoint" "endpoint" {
  name                 = "<endpoint-name>"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.config.name
}

resource "aws_appautoscaling_target" "endpoint" {
  service_namespace  = "sagemaker"
  resource_id        = "endpoint/<endpoint-name>/variant/AllTraffic"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  min_capacity       = 2
  max_capacity       = 8
}

resource "aws_appautoscaling_policy" "endpoint" {
  name               = "<endpoint-name>-scaling"
  service_namespace  = "sagemaker"
  resource_id        = aws_appautoscaling_target.endpoint.resource_id
  scalable_dimension = aws_appautoscaling_target.endpoint.scalable_dimension
  policy_type        = "TargetTrackingScaling"

  target_tracking_scaling_policy_configuration {
    target_value       = 14
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }
  }
}
```
