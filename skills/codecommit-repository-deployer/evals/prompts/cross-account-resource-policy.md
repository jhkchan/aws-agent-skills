# Eval: cross-account-resource-policy

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cross-account access: repository resource policy grants GitPull/GitPush, KMS key policy also grants cross-account principal (both required)

## Prompt

Configure cross-account access for CodeCommit repository
my-app-repo in us-east-1, account 123456789012, to grant access
to account 999999999999. The repository is encrypted with
customer-managed KMS key
arn:aws:kms:us-east-1:123456789012:key/abcd-1234. Grant
codecommit:GitPull and codecommit:GitPush to the cross-account
principal.
