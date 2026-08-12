# CloudTrail Diagnostic Commands

```bash
# Check trail status
aws cloudtrail describe-trails
aws cloudtrail get-trail-status --name <trail-name>

# Verify S3 bucket policy
aws s3api get-bucket-policy --bucket <log-bucket>

# Check event selectors
aws cloudtrail describe-trails --query 'trailList[*].[Name,EventSelectors]'

# Test event lookup
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=s3.amazonaws.com
```
