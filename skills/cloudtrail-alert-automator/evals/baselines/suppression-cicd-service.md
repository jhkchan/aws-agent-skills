# Baseline (no-skill) response: suppression-cicd-service

This file captures what a generic assistant produces WITHOUT the
cloudtrail-alert-automator skill loaded.

---

For suppressing CI/CD pipeline alerts, you can create an EventBridge
rule for UpdateStack and CreateChangeSet events. In your Lambda handler,
check if the userIdentity ARN matches your known CI/CD roles and skip
the alert if so.

Something like:

```python
if 'cicd-deploy-role' in event['detail']['userIdentity']['arn']:
    return  # skip alert
```

You could maintain a list of service roles to suppress. For dedup, you
might use DynamoDB with a TTL of 30 minutes or so.

Make sure you also log suppressed events somewhere so you have an audit
trail.
