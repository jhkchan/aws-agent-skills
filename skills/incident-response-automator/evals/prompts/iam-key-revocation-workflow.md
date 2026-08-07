# Eval prompt: iam-key-revocation-workflow

Design an automated incident response workflow. Emit the standard VERDICT
block.

Finding source: guardduty (finding type CredentialAccess:IAMUser/AnomalousBehavior)
Response scope: contain (revoke IAM access key + revoke active sessions)
Severity threshold: 7.0

Requirements:
- EventBridge rule pattern scoped to the specific finding type
- Two-step containment action:
  1. aws iam update-access-key --user-name <user> --access-key-id <AKIA...> --status Inactive
  2. aws iam put-user-policy with an inline policy that has Effect:Deny,
     Action:"*", Resource:"*" — forces active STS sessions to re-evaluate
     and effectively ends them
- Kill-switch: Parameter Store /ir/iam-kill-switch
- Manual override: SNS notification with task-token callback for analyst
  to confirm key re-enablement if the finding is a false positive
- Notification: SNS topic -> on-call pager (PagerDuty via SNS webhook)
- IAM role for Lambda: scoped to iam:UpdateAccessKey on
  arn:aws:iam::*:user/*, iam:PutUserPolicy, iam:DeleteUserPolicy (for
  rollback), sns:Publish
- Idempotency: Lambda checks if the key is already Inactive before
  re-deactivating; checks if the Deny-all policy is already attached
  before re-attaching
- Audit: every action includes the incident ID as a tag in CloudTrail
  (via a session tag IncidentId=<id> passed at AssumeRole time)
- Tested in security-test account (555555555555)

Expected: AUTOMATED. The workflow revokes both the static key (via
update-access-key) AND the active sessions (via put-user-policy Deny-all),
which is the correct two-step pattern. update-access-key alone does NOT
revoke active sessions.
