# Baseline (no-skill) response: auto-remediation-prod-impact

This file captures what a generic assistant produces WITHOUT the
cost-anomaly-detection-automator skill loaded.

---

You can set up a Lambda function that triggers when a Critical cost
anomaly fires. The Lambda would call `ec2 stop-instances` on all
running instances to cap your spend. Wire it to the SNS topic that
receives Critical anomaly alerts.

The Lambda would look something like:

```python
import boto3
ec2 = boto3.client('ec2')
def lambda_handler(event, context):
    ec2.stop_instances(InstanceIds=['i-xxx', 'i-yyy'])
```

You'll need to list all running instances and stop them. Make sure the
Lambda has the right IAM permissions. Test it first to make sure it
works before enabling it in production.
