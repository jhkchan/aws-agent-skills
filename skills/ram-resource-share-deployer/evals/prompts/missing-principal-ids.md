# Eval: missing-principal-ids

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — at least one principal (account ID, OU ARN, or Organization ARN) must be provided

## Prompt

Provision a RAM resource share in us-east-1. Name:
shared-subnets-prod. Resource type: ec2:Subnet. Resource
ARN: arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123.
I have not decided which accounts to share with yet. Allow
external principals: false. Use default managed permission.
Tags: Environment=production.
