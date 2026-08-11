# Eval: branch-protection-and-notification

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — branch protection (IAM deny push to main), notification rule to SNS (topic policy grants CodeStar), PR template, Lambda trigger (target policy grants CodeCommit)

## Prompt

Configure my-app-repo in us-east-1, account 123456789012, with
branch protection on main (deny direct GitPush, force PR
workflow), notification rule for pull-request-created and
pull-request-merged events to SNS topic
arn:aws:sns:us-east-1:123456789012:codecommit-notifications,
pull request template at .github/PULL_REQUEST_TEMPLATE.md, and a
repository trigger invoking Lambda function
arn:aws:lambda:us-east-1:123456789012:function:trigger-handler on
all events.
