# IAM Policies and SSE-KMS — Kinesis Stream Deployer

Deep reference on resource-level IAM policy templates (producer,
standard consumer, enhanced fan-out consumer), SSE-KMS key creation and
key policy configuration, and KMS permission delegation. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Producer IAM policy (write access)

The producer application needs permission to write records to the
stream. Minimum actions: `PutRecord` and `PutRecords`. Include
`DescribeStream` and `DescribeStreamSummary` for troubleshooting.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KinesisProducerAccess",
      "Effect": "Allow",
      "Action": [
        "kinesis:PutRecord",
        "kinesis:PutRecords",
        "kinesis:DescribeStream",
        "kinesis:DescribeStreamSummary",
        "kinesis:ListShards"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream"
    }
  ]
}
```

### Producer best practices

- Use `PutRecords` (batch) instead of `PutRecord` (single) for higher
  throughput and lower cost. `PutRecords` accepts up to 500 records or
  5 MiB per request.
- Handle partial failures in `PutRecords` responses — individual records
  can fail while the batch succeeds. Retry failed records with
  exponential backoff.
- Include `ListShards` if the producer needs to discover shard layout
  for partition key routing.

## Standard consumer IAM policy (GetRecords)

The standard consumer uses polling-based `GetRecords`. Minimum actions:
`GetRecords` and `GetShardIterator`. Include `DescribeStream` and
`ListShards` for shard discovery.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KinesisStandardConsumerAccess",
      "Effect": "Allow",
      "Action": [
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "kinesis:DescribeStream",
        "kinesis:DescribeStreamSummary",
        "kinesis:ListShards",
        "kinesis:ListStreams"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream"
    }
  ]
}
```

## Enhanced fan-out consumer IAM policy (SubscribeToShard)

Enhanced fan-out consumers use `SubscribeToShard` (HTTP/2 push) instead
of `GetRecords`. The IAM policy MUST include the consumer ARN in the
Resource list, not just the stream ARN.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KinesisEnhancedFanoutAccess",
      "Effect": "Allow",
      "Action": [
        "kinesis:SubscribeToShard",
        "kinesis:DescribeStream",
        "kinesis:DescribeStreamSummary",
        "kinesis:ListShards",
        "kinesis:ListStreams"
      ],
      "Resource": [
        "arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream",
        "arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream/consumer/*"
      ]
    }
  ]
}
```

**Critical:** the Resource list must include the consumer ARN pattern
(`stream/<name>/consumer/*`). Without it, `SubscribeToShard` returns
AccessDenied even if the stream ARN is allowed.

## SSE-KMS key creation

### Option 1: AWS-managed key (simplest)

Use `alias/aws/kinesis`. AWS creates and manages the key automatically.
No key policy to configure.

```bash
aws kinesis start-stream-encryption \
  --stream-name my-data-stream \
  --encryption-type KMS \
  --key-id alias/aws/kinesis \
  --region us-east-1
```

**Limitation:** the AWS-managed key cannot be customized, and you cannot
view its key policy or audit its usage as granularly as a CMK.

### Option 2: Customer-managed key (recommended for production)

Create a dedicated CMK with a key policy that permits the Kinesis
service.

```bash
# Create the CMK
KMS_KEY_ID=$(aws kms create-key \
  --description "Kinesis SSE-KMS key for my-data-stream" \
  --policy '{
    "Version": "2012-10-17",
    "Id": "kinesis-stream-encryption-key",
    "Statement": [
      {
        "Sid": "EnableIAMUserPermissions",
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::123456789012:root"
        },
        "Action": "kms:*",
        "Resource": "*"
      },
      {
        "Sid": "AllowKinesisServiceToUseKey",
        "Effect": "Allow",
        "Principal": {
          "Service": "kinesis.amazonaws.com"
        },
        "Action": [
          "kms:GenerateDataKey",
          "kms:Decrypt"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --query 'KeyMetadata.KeyId' --output text \
  --region us-east-1)

# Create an alias for readability
aws kms create-alias \
  --alias-name alias/kinesis/my-data-stream \
  --target-key-id "$KMS_KEY_ID" \
  --region us-east-1

# Enable encryption on the stream
aws kinesis start-stream-encryption \
  --stream-name my-data-stream \
  --encryption-type KMS \
  --key-id "$KMS_KEY_ID" \
  --region us-east-1
```

### Key policy explained

| Statement | Principal | Purpose |
|---|---|---|
| `EnableIAMUserPermissions` | Account root (`arn:aws:iam::<acct>:root`) | Allows account administrators to manage the key |
| `AllowKinesisServiceToUseKey` | `kinesis.amazonaws.com` | **Required** — allows Kinesis to encrypt/decrypt records |

Without the `AllowKinesisServiceToUseKey` statement, all PutRecord and
GetRecords calls fail with a KMS AccessDenied error.

### KMS permissions for producers and consumers

When using a CMK, the producer and consumer IAM identities ALSO need KMS
permissions. Add this statement to the producer and consumer IAM policies:

```json
{
  "Sid": "KMSAccessForKinesis",
  "Effect": "Allow",
  "Action": [
    "kms:GenerateDataKey",
    "kms:Decrypt"
  ],
  "Resource": "arn:aws:kms:us-east-1:123456789012:key/<key-id>"
}
```

**Common mistake:** the producer/consumer IAM policy has the Kinesis
actions on the stream ARN, but the KMS actions must reference the KMS
key ARN (a different resource). These are separate Resource fields.

## Verifying encryption status

```bash
# Check encryption type and key ID
aws kinesis describe-stream \
  --stream-name my-data-stream \
  --query 'StreamDescription.{EncryptionType:EncryptionType, KeyId:KeyId}' \
  --region us-east-1 --output table
```

Expected output:
```
---------------------------------------
|        DescribeStream              |
+---------------+-------------------+
| EncryptionType |      KeyId       |
+---------------+-------------------+
|     KMS       | alias/kinesis/... |
+---------------+-------------------+
```

If `EncryptionType` is `NONE`, encryption is not enabled.

## Stream resource policy (cross-account)

For cross-account access without IAM role assumption, use
`put-resource-policy`:

```bash
aws kinesis put-resource-policy \
  --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "CrossAccountReadAccess",
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::999999999999:root"
        },
        "Action": [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:SubscribeToShard",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards"
        ],
        "Resource": [
          "arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream",
          "arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream/consumer/*"
        ]
      }
    ]
  }' \
  --region us-east-1
```

**Important:** the consuming account's IAM principal STILL needs an
identity-based policy granting the same Kinesis actions. Both the
resource policy AND the identity-based policy must allow the action
(effective permission = intersection). This is the same model as S3
bucket policies + IAM policies.

## Terraform IAM examples

```hcl
# Producer IAM policy
resource "aws_iam_policy" "kinesis_producer" {
  name = "kinesis-producer-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards"
        ]
        Resource = aws_kinesis_stream.main.arn
      },
      {
        Effect = "Allow"
        Action = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource = aws_kms_key.kinesis.arn
      }
    ]
  })
}

# Enhanced fan-out consumer IAM policy
resource "aws_iam_policy" "kinesis_enhanced_consumer" {
  name = "kinesis-enhanced-consumer-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:SubscribeToShard",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards"
        ]
        Resource = [
          aws_kinesis_stream.main.arn,
          "${aws_kinesis_stream.main.arn}/consumer/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["kms:Decrypt"]
        Resource = aws_kms_key.kinesis.arn
      }
    ]
  })
}

# KMS key for Kinesis SSE
resource "aws_kms_key" "kinesis" {
  description             = "Kinesis SSE-KMS key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableIAMUserPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowKinesisService"
        Effect = "Allow"
        Principal = {
          Service = "kinesis.amazonaws.com"
        }
        Action   = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "kinesis" {
  name          = "alias/kinesis/my-data-stream"
  target_key_id = aws_kms_key.kinesis.key_id
}

# Stream with encryption
resource "aws_kinesis_stream" "main" {
  name             = "my-data-stream"
  retention_period = 168

  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  encryption_type = "KMS"
  kms_key_id      = aws_kms_key.kinesis.arn

  tags = {
    Environment = "production"
  }
}
```

## Common IAM pitfalls

1. **Missing `kinesis:DescribeStream`.** Without it, the KCL and most
   consumer libraries cannot discover shard information and fail to
   start. Always include it in both producer and consumer policies.

2. **Enhanced fan-out consumer missing consumer ARN.** The Resource list
   must include `stream/<name>/consumer/*`. Without it,
   `SubscribeToShard` returns AccessDenied.

3. **KMS key policy missing Kinesis service principal.** The CMK policy
   MUST allow `kinesis.amazonaws.com` to call `GenerateDataKey` and
   `Decrypt`. This is separate from the IAM identity-based policy.

4. **Producer/consumer missing KMS permissions.** When using a CMK, the
   producer needs `kms:GenerateDataKey` and the consumer needs
   `kms:Decrypt` on the KMS key ARN. These are in addition to the Kinesis
   actions on the stream ARN.

5. **Cross-account consumer missing identity-based policy.** A stream
   resource policy grants the stream's permission, but the consuming
   account's IAM principal ALSO needs an identity-based policy granting
   the Kinesis actions. Both must allow the action.
