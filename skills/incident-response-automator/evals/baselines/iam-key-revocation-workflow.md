# Baseline (no-skill) response: iam-key-revocation-workflow

This file captures what a generic assistant produces WITHOUT the
incident-response-automator skill loaded.

---

To automate IAM key revocation on suspicious activity, set up an
EventBridge rule that triggers a Lambda when GuardDuty detects
CredentialAccess findings. The Lambda should call
`aws iam update-access-key --status Inactive` to disable the key.
Here's the core logic:

```python
import boto3
iam = boto3.client('iam')
def lambda_handler(event, context):
    user = event['detail']['resource']['accessKeyDetails']['userName']
    key_id = event['detail']['resource']['accessKeyDetails']['accessKeyId']
    iam.update_access_key(UserName=user, AccessKeyId=key_id, Status='Inactive')
```

This disables the access key. You may want to send a notification too.
