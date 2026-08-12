# Eval: vpc-endpoint-private-access

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — both API and repositories VPC endpoints created, private DNS enabled, dual-endpoint requirement noted

## Prompt

Create a CodeArtifact domain internal-registry in us-east-1,
account 123456789012. Create a maven repository java-artifacts.
Set up VPC interface endpoints for private access in VPC
vpc-aaa11122, subnets subnet-aaa111 and subnet-bbb222, security
group sg-priv-1. Tags: Environment=production, Network=private.
