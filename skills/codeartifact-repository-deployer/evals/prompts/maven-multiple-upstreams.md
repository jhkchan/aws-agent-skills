# Eval: maven-multiple-upstreams

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — maven multi-hop upstreams + external connection

## Prompt

Provision a CodeArtifact maven repository named
team-payments-maven in us-east-1. Domain: shared (existing,
owner 123456789012). Multi-hop upstream chain:
team-payments-internal, then shared-maven (both already exist
in the domain), then the public:maven-central external
connection on shared-maven. CI role: payments-ci with
ReadFromRepository and GetAuthorizationToken. Release role:
payments-release with PublishPackageVersion. CI uses the
codeartifact login CLI for mvn. Tags: Environment=production,
Team=payments, Format=maven. Account: 123456789012.
