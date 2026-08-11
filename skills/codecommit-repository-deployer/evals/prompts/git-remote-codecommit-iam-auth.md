# Eval: git-remote-codecommit-iam-auth

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — GRC for developer auth (SSO/federated), IAM git credentials for CI pipeline, session-token based auth selection

## Prompt

Create a CodeCommit repository named platform-tools in us-east-1,
account 123456789012. Developers authenticate via SSO and should
use git-remote-codecommit (GRC). The CI pipeline uses a dedicated
IAM user ci-codecommit-user with static git credentials. Default
branch main. Tags: Environment=production.
