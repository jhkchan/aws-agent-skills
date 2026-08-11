# Eval: customer-managed-permissions-subnet

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ec2:Subnet, customer-managed permission allowing CreateNetworkInterface + DescribeSubnets, denying Delete

## Prompt

Provision a RAM resource share in us-east-1. Name:
shared-subnets-custom-perm. Resource type: ec2:Subnet.
Resources: arn:aws:ec2:us-east-1:123456789012:subnet/
subnet-abc123. Principals: OU
arn:aws:organizations::123456789012:ou/o-abc123def/ou-xyz456.
Create and associate a customer-managed permission named
custom-subnet-readonly that allows ec2:CreateNetworkInterface
and ec2:DescribeSubnets but denies ec2:DeleteNetworkInterface.
Allow external principals: false. Tags:
Environment=production.
