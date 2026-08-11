# Eval: subnet-share-with-accounts

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — ec2:Subnet, two account IDs, internal sharing, default managed permission

## Prompt

Provision a RAM resource share in us-east-1. Name:
shared-subnets-prod. Resource type: ec2:Subnet. Resources:
subnet-abc123 (arn:aws:ec2:us-east-1:123456789012:subnet/
subnet-abc123), subnet-def456 (arn:aws:ec2:us-east-1:
123456789012:subnet/subnet-def456). Principals: account IDs
111111111111, 222222222222. Same Organization, all features
enabled. Allow external principals: false. Use default AWS
managed permission for subnets. Tags:
Environment=production, Application=networking.
