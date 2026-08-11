# Eval: npm-repository-with-public-upstream

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — npm repo, external connection + internal upstream, IAM policies

## Prompt

Provision a CodeArtifact npm repository named shared-npm in
us-east-1. Domain: shared (existing, owner 123456789012).
Associate the public:npmjs external connection. Chain upstream
to shared-internal (an internal npm mirror repository that
already exists in the same domain). Repository consume access
for the ci-build IAM role. Repository publish access for the
release-pipeline IAM role. CI builds use the codeartifact
login CLI for npm. Tags: Environment=production, Format=npm.
Account: 123456789012.
