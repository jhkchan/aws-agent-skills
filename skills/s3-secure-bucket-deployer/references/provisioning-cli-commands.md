# Provisioning CLI Commands — S3 Secure Bucket Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<name>`, `<region>`, `<account-id>`,
`<logging-bucket>`, `<dest-bucket>`, `<dest-region>`, KMS key ARNs,
`<trail-name>`, tag key/values.

## Step 0: Prerequisites check

```bash
# Confirm account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm bucket name is available (should return 404 / error)
aws s3api head-bucket --bucket <name> 2>&1 || echo "Bucket name is available"
```

## Step 1: Create bucket + enable BPA

```bash
# Create bucket (omit LocationConstraint for us-east-1)
if [ "$REGION" = "us-east-1" ]; then
  aws s3api create-bucket --bucket <name>
else
  aws s3api create-bucket \
    --bucket <name> \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
fi

# Bucket-level BPA (immediately)
aws s3api put-public-access-block \
  --bucket <name> \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Account-level BPA (defense-in-depth)
aws s3control put-public-access-block \
  --account-id "$ACCOUNT_ID" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Step 2: Default encryption (SSE-KMS with Bucket Key)

```bash
aws s3api put-bucket-encryption \
  --bucket <name> \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms",
          "KMSMasterKeyID": "arn:aws:kms:<region>:<account-id>:key/<key-id>"
        },
        "BucketKeyEnabled": true
      }
    ]
  }'
```

For SSE-S3 (simpler, free):

```bash
aws s3api put-bucket-encryption \
  --bucket <name> \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }
    ]
  }'
```

## Step 3: Object Ownership — BucketOwnerEnforced

```bash
aws s3api put-bucket-ownership-controls \
  --bucket <name> \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]
```

## Step 4: Versioning

```bash
aws s3api put-bucket-versioning \
  --bucket <name> \
  --versioning-configuration Status=Enabled
```

MFA Delete (must be run as root account):

```bash
aws s3api put-bucket-versioning \
  --bucket <name> \
  --versioning-configuration Status=Enabled,MFADevice=<mfa-device-arn> \
  --mfa "<mfa-serial> <mfa-code>"
```

## Step 5: Logging bucket setup + access logging

First, set up the logging target bucket:

```bash
# Create logging bucket if it doesn't exist
aws s3api create-bucket --bucket <logging-bucket>

# Enable BPA on logging bucket too
aws s3api put-public-access-block \
  --bucket <logging-bucket> \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Grant S3 log delivery write access (bucket policy, since BucketOwnerEnforced disables ACLs)
aws s3api put-bucket-policy \
  --bucket <logging-bucket> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "logging.s3.amazonaws.com"},
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::<logging-bucket>/*"
      }
    ]
  }'
```

Then enable access logging on the data bucket:

```bash
aws s3api put-bucket-logging \
  --bucket <name> \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "<logging-bucket>",
      "TargetPrefix": "s3/<name>/"
    }
  }'
```

## Step 6: Bucket policy — HTTPS-only + SSE-KMS enforcement

### SSE-KMS bucket

```bash
aws s3api put-bucket-policy \
  --bucket <name> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "EnforceHTTPSConnections",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::<name>",
          "arn:aws:s3:::<name>/*"
        ],
        "Condition": {
          "Bool": {"aws:SecureTransport": false}
        }
      },
      {
        "Sid": "DenyUnEncryptedObjectUploads",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::<name>/*",
        "Condition": {
          "StringNotEquals": {
            "s3:x-amz-server-side-encryption": "aws:kms"
          }
        }
      }
    ]
  }'
```

### SSE-S3 bucket (HTTPS-only, no SSE enforcement)

```bash
aws s3api put-bucket-policy \
  --bucket <name> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "EnforceHTTPSConnections",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::<name>",
          "arn:aws:s3:::<name>/*"
        ],
        "Condition": {
          "Bool": {"aws:SecureTransport": false}
        }
      }
    ]
  }'
```

## Step 7: CloudTrail data events

```bash
aws cloudtrail put-event-selectors \
  --trail-name <trail-name> \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::S3::Object",
      "Values": ["arn:aws:s3:::<name>/"]
    }]
  }]'
```

## Step 8: Lifecycle policy

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket <name> \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "transition-current-versions",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER"},
          {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
        ],
        "Expiration": {"Days": 2555}
      },
      {
        "ID": "expire-noncurrent-versions",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "NoncurrentVersionTransitions": [
          {"NoncurrentDays": 30, "StorageClass": "STANDARD_IA"},
          {"NoncurrentDays": 90, "StorageClass": "GLACIER"}
        ],
        "NoncurrentVersionExpiration": {"NoncurrentDays": 180}
      },
      {
        "ID": "expire-delete-markers",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "Expiration": {"ExpiredObjectDeleteMarker": true}
      }
    ]
  }'
```

## Step 9: Replication (CRR)

### Create replication IAM role

```bash
aws iam create-role \
  --role-name <name>-replication-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name <name>-replication-role \
  --policy-name <name>-replication-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetReplicationConfiguration", "s3:ListBucket"],
        "Resource": "arn:aws:s3:::<name>"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:GetObjectVersionForReplication", "s3:GetObjectVersionAcl", "s3:GetObjectVersionTagging"],
        "Resource": "arn:aws:s3:::<name>/*"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:ReplicateObject", "s3:ReplicateDelete", "s3:ReplicateTags"],
        "Resource": "arn:aws:s3:::<dest-bucket>/*"
      },
      {
        "Effect": "Allow",
        "Action": ["kms:Decrypt", "kms:DescribeKey"],
        "Resource": "arn:aws:kms:<region>:<account-id>:key/<source-key-id>"
      },
      {
        "Effect": "Allow",
        "Action": ["kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
        "Resource": "arn:aws:kms:<dest-region>:<account-id>:key/<dest-key-id>"
      }
    ]
  }'
```

### Configure replication

```bash
aws s3api put-bucket-replication \
  --bucket <name> \
  --replication-configuration '{
    "Role": "arn:aws:iam::<account-id>:role/<name>-replication-role",
    "Rules": [
      {
        "ID": "replicate-all",
        "Status": "Enabled",
        "Priority": 1,
        "Filter": {"Prefix": ""},
        "Destination": {
          "Bucket": "arn:aws:s3:::<dest-bucket>",
          "EncryptionConfiguration": {
            "ReplicaKmsKeyID": "arn:aws:kms:<dest-region>:<account-id>:key/<dest-key-id>"
          }
        },
        "DeleteMarkerReplication": {"Status": "Enabled"}
      }
    ]
  }'
```

## Step 10: Tags

```bash
aws s3api put-bucket-tagging \
  --bucket <name> \
  --tagging '{
    "TagSet": [
      {"Key": "Environment", "Value": "production"},
      {"Key": "Workload", "Value": "general-purpose"},
      {"Key": "DataClassification", "Value": "confidential"},
      {"Key": "Owner", "Value": "platform-team"},
      {"Key": "CostCenter", "Value": "12345"}
    ]
  }'
```

## Verification

```bash
aws s3api get-public-access-block          --bucket <name>
aws s3control get-public-access-block      --account-id <account-id>
aws s3api get-bucket-encryption            --bucket <name>
aws s3api get-bucket-ownership-controls    --bucket <name>
aws s3api get-bucket-versioning            --bucket <name>
aws s3api get-bucket-policy                --bucket <name>
aws s3api get-bucket-logging               --bucket <name>
aws s3api get-bucket-lifecycle-configuration --bucket <name>
aws s3api get-bucket-replication           --bucket <name>
aws s3api get-bucket-tagging               --bucket <name>
aws cloudtrail get-event-selectors         --trail-name <trail-name>
aws s3api get-bucket-location              --bucket <name>
```

## Terraform equivalent (aws_s3_bucket + associated resources)

The same configuration as Terraform (for IaC-managed deployments):

```hcl
resource "aws_s3_bucket" "secure" {
  bucket = "<name>"
}

resource "aws_s3_bucket_public_access_block" "secure" {
  bucket                  = aws_s3_bucket.secure.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "secure" {
  bucket = aws_s3_bucket.secure.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "secure" {
  bucket = aws_s3_bucket.secure.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secure" {
  bucket = aws_s3_bucket.secure.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_policy" "secure" {
  bucket = aws_s3_bucket.secure.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceHTTPSConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.secure.arn,
          "${aws_s3_bucket.secure.arn}/*"
        ]
        Condition = {
          Bool = { aws:SecureTransport = false }
        }
      },
      {
        Sid       = "DenyUnEncryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.secure.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "secure" {
  bucket = aws_s3_bucket.secure.id

  rule {
    id     = "transition-current"
    status = "Enabled"
    filter { prefix = "" }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration {
      days = 2555
    }
  }

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    filter { prefix = "" }
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }
    noncurrent_version_expiration {
      noncurrent_days = 180
    }
  }
}
```
