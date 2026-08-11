# Provisioning CLI Commands — S3 Bucket Policy Deployer

Full copy-pasteable CLI command sequence for provisioning S3 bucket
policies with HTTPS-only enforcement, cross-account access,
VPC-endpoint-only restrictions, CloudFront OAC, service access, ACL
disablement, and Access Points / MRAP delegation. Variables to
substitute: `<bucket-name>`, `<account-id>`, `<region>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm bucket exists
aws s3api head-bucket --bucket my-bucket

# Check Block Public Access posture
aws s3api get-public-access-block --bucket my-bucket

# Check object ownership (should be BucketOwnerEnforced)
aws s3api get-bucket-ownership-controls --bucket my-bucket

# Validate policy JSON and size
python3 -m json.tool policy.json && wc -c policy.json
```

## Step 1: Disable ACLs (BucketOwnerEnforced)

```bash
aws s3api put-bucket-ownership-controls \
  --bucket my-bucket \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]
```

## Step 2: Apply HTTPS-only + cross-account + CloudFront OAC policy

```bash
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DenyInsecureTransport",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::my-bucket",
          "arn:aws:s3:::my-bucket/*"
        ],
        "Condition": {
          "Bool": { "aws:SecureTransport": "false" }
        }
      },
      {
        "Sid": "AllowCrossAccountWithExternalId",
        "Effect": "Allow",
        "Principal": { "AWS": "arn:aws:iam::998877665544:role/PartnerRole" },
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": [
          "arn:aws:s3:::my-bucket",
          "arn:aws:s3:::my-bucket/shared/*"
        ],
        "Condition": {
          "StringEquals": { "aws:ExternalId": "unique-external-id-12345" }
        }
      },
      {
        "Sid": "AllowCloudFrontOAC",
        "Effect": "Allow",
        "Principal": { "Service": "cloudfront.amazonaws.com" },
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-bucket/*",
        "Condition": {
          "StringEquals": {
            "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/E123ABCDEF456"
          }
        }
      }
    ]
  }'
```

## Step 3: VPC-endpoint-only policy

```bash
aws s3api put-bucket-policy \
  --bucket my-private-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DenyNotFromVpcEndpoint",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::my-private-bucket",
          "arn:aws:s3:::my-private-bucket/*"
        ],
        "Condition": {
          "StringNotEquals": { "aws:SourceVpce": "vpce-0abc123def456" }
        }
      }
    ]
  }'
```

## Step 4: AWS service access (logging with s3:x-amz-acl)

```bash
aws s3api put-bucket-policy \
  --bucket my-logs-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowLoggingServiceWithACL",
        "Effect": "Allow",
        "Principal": { "Service": "logging.amazonaws.com" },
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::my-logs-bucket/logs/*",
        "Condition": {
          "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control" }
        }
      }
    ]
  }'
```

## Step 5: CloudFront OAC setup (CloudFront side)

```bash
# Create the OAC config in CloudFront
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "my-bucket-oac",
    "Description": "OAC for my-bucket",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always",
    "OriginAccessControlOriginType": "s3"
  }' \
  --query 'OriginAccessControl.Id' --output text)

echo "OAC ID: $OAC_ID"

# Verify the OAC exists
aws cloudfront get-origin-access-control --id "$OAC_ID"
```

## Step 6: Enable Block Public Access

```bash
aws s3api put-public-access-block \
  --bucket my-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Step 7: Access Points policy delegation

```bash
# Attach a policy to an existing access point
aws s3control put-access-point-policy \
  --account-id 123456789012 \
  --name team-a-ap \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/TeamARole" },
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:us-east-1:123456789012:accesspoint/team-a-ap/team-a/*"
    }]
  }'
```

## Step 8: MRAP policy

```bash
aws s3control put-multi-region-access-point-policy \
  --account-id 123456789012 \
  --details Name=my-mrap,Policy='{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/GlobalApp" },
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3::123456789012:accesspoint/my-mrap"
    }]
  }'
```

## Step 9: Verification

```bash
# Verify the bucket policy
aws s3api get-bucket-policy --bucket my-bucket --query Policy --output text | python3 -m json.tool

# Verify Block Public Access
aws s3api get-public-access-block --bucket my-bucket

# Verify object ownership
aws s3api get-bucket-ownership-controls --bucket my-bucket

# Verify CloudFront OAC
aws cloudfront get-origin-access-control --id E123ABCDEF456

# Verify access point policy
aws s3control get-access-point-policy --account-id 123456789012 --name team-a-ap

# Verify MRAP policy
aws s3control get-multi-region-access-point-policy --account-id 123456789012 --name my-mrap
```

## Terraform equivalent

```hcl
resource "aws_s3_bucket_policy" "main" {
  bucket = aws_s3_bucket.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*"
        ]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      },
      {
        Sid       = "AllowCloudFrontOAC"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.main.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = "arn:aws:cloudfront::123456789012:distribution/E123ABCDEF456"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_ownership_controls" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket                  = aws_s3_bucket.main.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Put bucket policy | `aws s3api put-bucket-policy` |
| Get bucket policy | `aws s3api get-bucket-policy` |
| Delete bucket policy | `aws s3api delete-bucket-policy` |
| Put public access block | `aws s3api put-public-access-block` |
| Put ownership controls | `aws s3api put-bucket-ownership-controls` |
| Put AP policy | `aws s3control put-access-point-policy` |
| Put MRAP policy | `aws s3control put-multi-region-access-point-policy` |
| Create OAC | `aws cloudfront create-origin-access-control` |
| Get OAC | `aws cloudfront get-origin-access-control` |
| Validate JSON | `python3 -m json.tool policy.json` |
