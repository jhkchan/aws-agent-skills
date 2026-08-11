# Provisioning CLI Commands Reference

Supplementary reference for the S3 Directory Bucket Deployer skill.
Copy-pasteable AWS CLI v2 commands organized by provisioning step.

## Pre-flight: verify AZ, region, and account state

```bash
# Resolve AZ ID from AZ name (account-specific mapping)
aws ec2 describe-availability-zones \
  --zone-names us-east-1a \
  --query 'AvailabilityZones[0].[ZoneName,ZoneId]' --output text

# List all AZs in a region
aws ec2 describe-availability-zones \
  --region us-east-1 \
  --query 'AvailabilityZones[].[ZoneName,ZoneId]' --output table

# Account ID
aws sts get-caller-identity --query Account --output text

# Verify region supports S3 Express One Zone
aws s3api list-buckets --region us-east-1 --output json
```

## Step 2: construct the directory bucket name

```bash
BASE_NAME="my-app-data"
AZ_ID="use1-az1"
DIRECTORY_BUCKET="${BASE_NAME}--${AZ_ID}--x-s3"
echo "$DIRECTORY_BUCKET"
# my-app-data--use1-az1--x-s3
```

Validation rules:
- Base name contains NO double-dash (`--`)
- Base name is DNS-compatible (lowercase, alphanumeric, hyphens)
- AZ ID is in `xxxx-azN` format (e.g., `use1-az1`)
- Suffix is exactly `--x-s3`

## Step 3: create the directory bucket

```bash
# S3 Express One Zone directory bucket
aws s3api create-directory-bucket \
  --bucket my-app-data--use1-az1--x-s3 \
  --data-redundancy SingleAvailabilityZone \
  --region us-east-1
```

Do NOT use `create-bucket` — it creates a general-purpose S3 bucket
with no Express One Zone benefits, and the operation succeeds silently.

## Step 4: encryption and bucket policy

```bash
# Default encryption (SSE-KMS)
aws s3api put-bucket-encryption \
  --bucket my-app-data--use1-az1--x-s3 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:111111111111:key/<KEY_ID>"
      }
    }]
  }'

# Bucket policy (s3express ARN format — NOT standard s3 ARN)
aws s3api put-bucket-policy \
  --bucket my-app-data--use1-az1--x-s3 \
  --policy file://directory-bucket-policy.json
```

`directory-bucket-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111111111111:role/<APP_ROLE>"},
    "Action": ["s3express:GetObject", "s3express:PutObject", "s3express:ListBucket"],
    "Resource": [
      "arn:aws:s3express:us-east-1:111111111111:my-app-data--use1-az1--x-s3",
      "arn:aws:s3express:us-east-1:111111111111:my-app-data--use1-az1--x-s3/*"
    ]
  }]
}
```

**Critical:** the ARN uses `s3express` service prefix, not `s3`. A
standard `arn:aws:s3:::<bucket>` ARN matches nothing on a directory
bucket.

## Step 5: zone-affinity compute

```bash
# Find subnets in the target AZ
aws ec2 describe-subnets \
  --filters Name=availability-zone-id,Values=use1-az1 \
  --query 'Subnets[].[SubnetId,AvailabilityZoneId,CidrBlock]' --output table

# Launch EC2 in the same AZ
aws ec2 run-instances \
  --image-id ami-<AMI_ID> \
  --instance-type c7n.large \
  --subnet-id subnet-<SUBNET_IN_TARGET_AZ> \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=zone-affinity-app}]"

# Create a capacity reservation in the target AZ (optional, guarantees capacity)
aws ec2 create-capacity-reservation \
  --instance-type c7n.large \
  --availability-zone-id use1-az1 \
  --instance-platform Linux/UNIX \
  --instance-count 4
```

For ECS: constrain the task placement or node group to the target AZ.
For EKS: use a node group with subnets only in the target AZ.

## Step 6: table buckets (S3 Tables / Apache Iceberg)

```bash
# Create a table bucket via the S3 Tables API (NOT s3api)
aws s3tables create-table-bucket \
  --name analytics-iceberg-tables \
  --region use1-az1

# Create an Iceberg table
aws s3tables create-table \
  --table-bucket-name analytics-iceberg-tables \
  --name events_iceberg \
  --format ICEBERG \
  --metadata '{"format-version":"2","write.ordering":"event_ts"}'

# List tables in the table bucket
aws s3tables list-tables \
  --table-bucket-name analytics-iceberg-tables
```

Table buckets do NOT support `PutObject`/`GetObject`. Access Iceberg
tables via Athena, Glue, Spark, or Trino integrations.

## Step 8: verification

```bash
# Verify bucket type is Directory (not general-purpose)
aws s3api list-buckets \
  --query 'Buckets[?Name==`my-app-data--use1-az1--x-s3`]' --output json

# Verify encryption
aws s3api get-bucket-encryption \
  --bucket my-app-data--use1-az1--x-s3

# Verify bucket policy
aws s3api get-bucket-policy \
  --bucket my-app-data--use1-az1--x-s3

# Verify compute AZ matches bucket AZ
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=zone-affinity-app" \
  --query 'Reservations[].Instances[].[InstanceId,Placement.AvailabilityZone,Placement.AvailabilityZoneId]' \
  --output table

# Latency probe (from same-AZ compute — should be single-digit ms)
time aws s3 ls s3://my-app-data--use1-az1--x-s3/ --region us-east-1

# For table buckets: verify table
aws s3tables list-tables --table-bucket-name analytics-iceberg-tables
```

## Rollback

```bash
# Delete the directory bucket (must be empty)
aws s3api delete-directory-bucket \
  --bucket my-app-data--use1-az1--x-s3

# For table buckets: delete tables first, then the table bucket
aws s3tables delete-table \
  --table-bucket-name analytics-iceberg-tables \
  --name events_iceberg

aws s3tables delete-table-bucket \
  --name analytics-iceberg-tables \
  --region use1-az1

# Remove capacity reservation (if created)
aws ec2 cancel-capacity-reservation \
  --capacity-reservation-id cr-<ID>
```

## AZ name to AZ ID reference (account-specific — always verify)

| Region | AZ Name (example) | AZ ID (example) |
|---|---|---|
| us-east-1 | us-east-1a | use1-az1 (varies by account) |
| us-west-2 | us-west-2a | usw2-az1 (varies by account) |
| eu-west-1 | eu-west-1a | euw1-az1 (varies by account) |
| ap-southeast-2 | ap-southeast-2a | apse2-az1 (varies by account) |

**Always resolve with `ec2 describe-availability-zones`.** The mapping
is consistent within an account but varies across accounts.
