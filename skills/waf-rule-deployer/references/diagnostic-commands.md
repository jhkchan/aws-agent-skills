# Diagnostic and Verification Commands - waf-rule-deployer

## Step 4 - check current WCU usage (moved from SKILL.md)

```bash
# Check current WCU usage
aws wafv2 describe-web-acl \
  --scope CLOUDFRONT --region us-east-1 \
  --id <acl-id> \
  --query 'WebACL.Capacity' --output text
```

## Step 11 - Firehose logging configuration CLI (moved from SKILL.md)

```bash
# Create the Firehose stream (if needed)
aws firehose create-delivery-stream \
  --delivery-stream-name aws-waf-logs-production \
  --s3-destination-configuration \
    RoleARN=arn:aws:iam::<acct>:role/firehose-waf-role,\
    BucketARN=arn:aws:s3:::waf-logs-bucket \
  --region us-east-1

# Enable logging
aws wafv2 put-logging-configuration \
  --web-acl-arn <web-acl-arn> \
  --logging-configuration \
    LogDestinationConfigs=arn:aws:firehose:us-east-1:<acct>:deliverystream/aws-waf-logs-production \
  --region us-east-1
```

## Step 12 - CloudFront association and verification CLI (moved from SKILL.md)

```bash
aws wafv2 associate-web-acl \
  --web-acl-arn <web-acl-arn> \
  --resource-arn arn:aws:cloudfront::<acct>:distribution/E1234567890 \
  --region us-east-1

# Verify
aws wafv2 get-web-acl-for-resource \
  --resource-arn arn:aws:cloudfront::<acct>:distribution/E1234567890 \
  --region us-east-1 \
  --query 'WebACL.WebACLArn' --output text
```
