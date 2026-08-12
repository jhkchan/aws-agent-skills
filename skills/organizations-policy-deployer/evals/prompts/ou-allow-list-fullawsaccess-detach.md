# Eval: ou-allow-list-fullawsaccess-detach

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Allow-list strategy at OU (FullAWSAccess detached AFTER Allow-list attached), IAM/EC2/S3/RDS/Logs permitted

## Prompt

Create an SCP named prod-data-allowlist that allows only
ec2:*, s3:*, rds:*, iam:*, and logs:Describe* for the
OU_Prod_Data (ou-prod-data-001). This is an Allow-list
strategy — detach FullAWSAccess AFTER attaching the Allow-list.
Management account 123456789012. Tag the policy
Posture=allow-list.
