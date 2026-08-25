# Endpoint Deployment and Security — Comprehend Classifier Deployer

Deep reference on real-time endpoint configuration, auto-scaling, batch
inference job management, KMS encryption (model artifacts and training
volume), VPC endpoint for private inference, and IAM role scoping.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Endpoint configuration

### Creating an endpoint

```bash
aws comprehend create-endpoint \
  --endpoint-name "ticket-classifier-endpoint" \
  --model-arn "$CLASSIFIER_ARN" \
  --desired-inference-units 1 \
  --data-access-role-arn arn:aws:iam::123456789012:role/ComprehendEndpointRole \
  --region us-east-1
```

- `--desired-inference-units`: the number of inference units. Each
  unit provides a throughput of 100 characters per second for
  real-time classification.
- The endpoint takes 10-20 minutes to become IN_SERVICE.
- The endpoint charges per inference-unit-hour from IN_SERVICE time.

### Updating an endpoint (new model version)

```bash
aws comprehend update-endpoint \
  --endpoint-arn "$ENDPOINT_ARN" \
  --desired-model-arn "$NEW_CLASSIFIER_ARN" \
  --desired-inference-units 2 \
  --region us-east-1
```

- Updating the model ARN triggers a blue/green deployment.
- The old endpoint stays IN_SERVICE until the new one is ready.
- You can also change the number of inference units.

### Classifying a document (real-time)

```bash
aws comprehend classify-document \
  --endpoint-arn "$ENDPOINT_ARN" \
  --text "I need a refund for invoice #12345" \
  --region us-east-1
```

Response:

```json
{
  "Classes": [
    {"Name": "billing", "Score": 0.95},
    {"Name": "technical", "Score": 0.03},
    {"Name": "general", "Score": 0.02}
  ]
}
```

For multi-label, the response includes all labels with their scores.
You can threshold each label independently (e.g., assign a label only
if score > 0.7).

### Deleting an endpoint (stop charges)

```bash
aws comprehend delete-endpoint \
  --endpoint-arn "$ENDPOINT_ARN" \
  --region us-east-1
```

**Critical:** the endpoint charges per hour while IN_SERVICE. If you
are not using it, delete it. There is no "pause" — delete to stop
charges, recreate when needed.

## Auto-scaling

### Registering a scalable target

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --min-capacity 1 \
  --max-capacity 5
```

### Target tracking policy

```bash
aws application-autoscaling put-scaling-policy \
  --policy-name "comprehend-endpoint-scaling" \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 50.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ComprehendApproximateBacklogSize"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

- `TargetValue`: the target backlog size per inference unit. When the
  backlog exceeds this, auto-scaling adds units. When it drops below,
  it removes units.
- `ScaleInCooldown`: wait time (seconds) before scaling in after a
  scale-in event. Prevents flapping.
- `ScaleOutCooldown`: wait time before scaling out after a scale-out
  event.

## Batch inference

### Starting a batch job

```bash
aws comprehend classify-documents \
  --job-name "batch-classify-2026-08" \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --input-data-config S3Uri=s3://my-bucket/comprehend/input/ \
  --output-data-config S3Uri=s3://my-bucket/comprehend/output/ \
  --data-access-role-arn arn:aws:iam::123456789012:role/ComprehendBatchRole \
  --region us-east-1
```

- Input: one document per file in the input S3 path. Comprehend
  processes all files in the path.
- Output: JSONL files in the output S3 path. Each line is the
  classification result for one input document.
- Use a unique output prefix per batch run to avoid overwriting
  previous results.
- Batch jobs can take minutes to hours depending on document volume.

### Monitoring batch job status

```bash
aws comprehend describe-document-classification-job \
  --job-id "$JOB_ID" \
  --query 'DocumentClassificationJobProperties.JobStatus' \
  --region us-east-1
# SUBMITTED → IN_PROGRESS → COMPLETED (or FAILED)
```

## KMS encryption

### Model artifacts encryption

```bash
aws comprehend create-document-classifier \
  --model-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  ...
```

- Encrypts the trained model artifacts stored by Comprehend.
- Without this, artifacts use an AWS-managed key you cannot audit.

### Volume encryption

```bash
aws comprehend create-document-classifier \
  --volume-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  ...
```

- Encrypts the EBS volume used during training.
- Required for compliance-sensitive workloads (HIPAA, PCI, FedRAMP).

### KMS key policy

The KMS key policy must allow the Comprehend service to use the key:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "comprehend.amazonaws.com" },
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "*"
    }
  ]
}
```

The IAM role assumed by Comprehend must also have kms:Decrypt and
kms:GenerateDataKey permissions.

## VPC endpoint for private inference

### Creating a VPC endpoint

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.comprehend \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-comprehend \
  --private-dns-enabled \
  --region us-east-1
```

- `--private-dns-enabled`: enables private DNS resolution so the
  Comprehend service DNS name resolves to the VPC endpoint's private
  IP. This is required for the AWS SDK/CLI to route calls through the
  VPC endpoint automatically.
- Security group must allow inbound TCP 443 from the calling resource
  (Lambda function, EC2 instance, ECS task).

### VPC config for training jobs

```bash
aws comprehend create-document-classifier \
  --vpc-config '{"SecurityGroupIds":["sg-abc123"],"Subnets":["subnet-aaa","subnet-bbb"]}' \
  ...
```

- The training job runs in the specified subnets.
- The security group must allow outbound HTTPS (443) to S3 and
  Comprehend service endpoints.
- KMS key must be accessible from the VPC (key policy must allow the
  VPC endpoint).

## IAM role scoping

### Training role (broad — needs S3 + KMS)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/comprehend/training/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/abcd1234"
    }
  ]
}
```

### Endpoint role (narrow — inference only)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["comprehend:DetectDominantLanguage", "comprehend:ClassifyDocument"],
      "Resource": "*"
    }
  ]
}
```

### Batch role (S3 read input + write output)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/comprehend/input/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": ["arn:aws:s3:::my-bucket/comprehend/output/*"]
    }
  ]
}
```

**Common mistake:** using the training role (with broad S3 read) for
the endpoint. The endpoint does NOT need S3 access. Scope the endpoint
role to comprehend inference only.

## Cost comparison: endpoint vs batch

| Scenario | Endpoint cost | Batch cost | Winner |
|---|---|---|---|
| Real-time API (100 req/min, 24/7) | ~$365/month (1 IU) | Not suitable (latency) | Endpoint |
| Nightly batch (100k docs) | ~$365/month (idle 23 hrs) | ~$50/batch | Batch |
| Hourly batch (10k docs) | ~$365/month (mostly idle) | ~$5/hour-run | Batch |
| Intermittent (100 docs/day) | ~$365/month (idle) | ~$0.50/day-run | Batch |
| High-throughput (1000 req/min) | ~$1825/month (5 IU) | Not suitable (latency) | Endpoint |

**Rule of thumb:** if you need sub-second latency for user-facing
applications, use endpoint. If you process documents in bulk on a
schedule, use batch. For anything in between, calculate the breakeven:
endpoint cost (per hour) vs batch cost (per document).

## Step 6 — Endpoint deployment and auto-scaling (moved from SKILL.md)

Deploy a real-time inference endpoint for sub-second classification.

```bash
ENDPOINT_ARN=$(aws comprehend create-endpoint \
  --endpoint-name "ticket-classifier-endpoint" \
  --model-arn "$CLASSIFIER_ARN" \
  --desired-inference-units 1 \
  --data-access-role-arn arn:aws:iam::123456789012:role/ComprehendEndpointRole \
  --region us-east-1 \
  --query 'EndpointArn' --output text)
```

**Verify endpoint status:**

```bash
aws comprehend describe-endpoint \
  --endpoint-arn "$ENDPOINT_ARN" \
  --query 'EndpointProperties.Status' \
  --region us-east-1
# Expected: CREATING → IN_SERVICE
```

**Classify a document (real-time):**

```bash
aws comprehend classify-document \
  --endpoint-arn "$ENDPOINT_ARN" \
  --text "I need a refund for invoice #12345" \
  --region us-east-1
```

**Auto-scaling (Application Auto Scaling):**

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-classifier-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --min-capacity 1 --max-capacity 5

aws application-autoscaling put-scaling-policy \
  --policy-name "comprehend-scaling" \
  --service-namespace comprehend \
  --resource-id "arn:aws:comprehend:us-east-1:123456789012:document-endpoint/ticket-classifier-endpoint" \
  --scalable-dimension "comprehend:document-classifier-endpoint:DesiredInferenceUnits" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":50.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ComprehendApproximateBacklogSize"},"ScaleInCooldown":300,"ScaleOutCooldown":60}'
```

## Step 7 — Batch inference job (moved from SKILL.md)

Run asynchronous classification on documents in S3.

```bash
JOB_ID=$(aws comprehend classify-documents \
  --job-name "batch-classify-2026-08" \
  --document-classifier-arn "$CLASSIFIER_ARN" \
  --input-data-config S3Uri=s3://my-bucket/comprehend/input/ \
  --output-data-config S3Uri=s3://my-bucket/comprehend/output/ \
  --data-access-role-arn arn:aws:iam::123456789012:role/ComprehendBatchRole \
  --region us-east-1 \
  --query 'JobId' --output text)
```

**Monitor batch job:**

```bash
aws comprehend describe-document-classification-job \
  --job-id "$JOB_ID" \
  --query 'DocumentClassificationJobProperties.JobStatus' \
  --region us-east-1
# Expected: SUBMITTED → IN_PROGRESS → COMPLETED (or FAILED)
```

Batch output: JSONL files in the output S3 path, one classification
result per line. Use a unique output prefix per batch run to avoid
overwriting previous results.

## Step 8 — KMS encryption and VPC endpoint (moved from SKILL.md)

**KMS encryption:** use `--model-kms-key-id` for model artifacts and
`--volume-kms-key-id` for the EBS volume during training. The IAM role
must have `kms:Decrypt` and `kms:GenerateDataKey` on the key.

**VPC endpoint for private Comprehend API access:**

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.comprehend \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-comprehend \
  --region us-east-1
```

This enables inference calls from within the VPC to stay on the AWS
network (no internet gateway needed). The security group must allow
inbound 443 from the calling resource.

**VPC config for training job:** add `--vpc-config` to create-document-
classifier to run training entirely within a VPC.

## Step 9 — IAM roles and versioning (moved from SKILL.md)

**Training role trust policy** must allow `comprehend.amazonaws.com` to
assume. Permissions: `s3:GetObject` and `s3:ListBucket` on the training
data bucket, plus `kms:Decrypt`/`kms:GenerateDataKey` on the KMS key
(if encrypting). Scope to the specific bucket — avoid `s3:*`.

**Endpoint role** only needs `comprehend:Detect*` permissions. It does
NOT need S3 access. Over-privileged endpoint roles are a security risk.

**Versioning:** each `create-document-classifier` call with the same
name creates a new immutable version. The latest version is the
default. To use a specific version, include the version suffix in the
ARN. Old versions incur storage cost — delete unused versions.

```bash
# List all versions
aws comprehend list-document-classifiers \
  --query 'DocumentClassifierPropertiesList[*].{Name:DocumentClassifierName,Version:Version,Status:Status}' \
  --region us-east-1

# Delete a specific version
aws comprehend delete-document-classifier \
  --document-classifier-arn "arn:aws:comprehend:us-east-1:123456789012:document-classifier/my-classifier/version/1"
```
