# Eval: cross-account-domain-share

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — RAM resource share + consumer IAM

## Prompt

Share the existing CodeArtifact domain named shared (owner
123456789012) with consumer account 123456789012 in us-east-1.
Use a RAM resource share named codeartifact-shared-domain.
The consumer account's IAM role consumer-ci-build needs
codeartifact:GetAuthorizationToken and
codeartifact:ReadFromRepository on the shared domain's ARN
(with owner account ID 123456789012 embedded). The consumer
uses `aws codeartifact login --tool npm --domain shared
--domain-owner 123456789012 --repository shared-npm`. Account:
123456789012 (owner).
