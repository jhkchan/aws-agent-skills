# Eval: cross-account-repository-policy

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — domain owner grants read access to consumer account via repository policy, consumer login uses domain owner account ID

## Prompt

Create a CodeArtifact domain shared-artifacts in us-east-1,
owner account 123456789012. Create a pip repository
data-science-pkgs. Grant read access to consumer account
999999999999 via repository policy. The consumer should use
aws codeartifact login with the domain owner account ID.
Tags: Environment=production.
