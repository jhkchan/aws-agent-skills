# Baseline (no-skill) response: auto-tag-on-create

This file captures what a generic assistant produces WITHOUT the
tag-governance-automator skill loaded.

---

You can set up an EventBridge rule that triggers on CloudTrail API
calls for resource creation. When EC2 RunInstances, S3 CreateBucket,
or Lambda CreateFunction fires, invoke a Lambda function that adds
tags based on the creator identity.

The Lambda function would extract the user ARN from the event and
call the appropriate tagging API. For EC2 it's create-tags, for S3
it's put-bucket-tagging.

Something like:

```python
def lambda_handler(event, context):
    user = event['detail']['userIdentity']['arn']
    ec2.create_tags(...)
```

You'll need IAM permissions for the Lambda to tag resources. I don't
remember the exact event structure offhand — you'd need to check the
CloudTrail event format for each service.
