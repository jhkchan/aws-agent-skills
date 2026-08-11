# Eval: automated-remediation-step-functions

**Difficulty:** hard
**Branch:** COMPLETED — EventBridge + Step Functions remediation verified: test finding triggered object quarantine and SNS notification

## Prompt

We already have Macie enabled and Step Functions state machine
macie-remediation-workflow deployed. The EventBridge rule
macie-finding-trigger routes high-severity Macie findings to the Step
Functions workflow. Verify the integration is working: we generated a
test finding (sensitiveData:S3Object/Credit_Card on a public bucket),
and the workflow quarantined the object and sent an SNS notification.
Confirm post-verification passed. Account: 123456789012. Region:
us-east-1.
