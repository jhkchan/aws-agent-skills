# Eval: standard-repo-with-kms

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — standard repo with customer-managed KMS key (policy grants CodeCommit), approval rule template (2 reviewers) associated, branch protection on main

## Prompt

Create a CodeCommit repository named my-app-repo in us-east-1,
account 123456789012. Default branch main. Description
"Microservice repository for my-app". KMS encryption with
customer-managed key arn:aws:kms:us-east-1:123456789012:key/abcd-1234.
Approval rule template require-two-reviewers (2 approvals from
pool alice, bob). Branch protection on main (deny direct push).
Tags: Environment=production, Team=platform.
