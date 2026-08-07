# Baseline (no-skill) response: guardduty-ec2-quarantine

This file captures what a generic assistant produces WITHOUT the
incident-response-automator skill loaded.

---

To automate EC2 quarantine on GuardDuty findings, you can set up an
EventBridge rule that triggers a Lambda function when a high-severity
finding arrives. The Lambda can call ec2:ModifyInstanceAttribute to
swap the security group to a quarantine group. You'll need to create
the quarantine security group in advance. Here's some pseudo-code for
the Lambda:

```python
import boto3
ec2 = boto3.client('ec2')
def lambda_handler(event, context):
    instance_id = event['detail']['resource']['instanceDetails']['instanceId']
    ec2.modify_instance_attribute(InstanceId=instance_id, Groups=['sg-quarantine'])
```

Make sure to give the Lambda the right IAM permissions.
