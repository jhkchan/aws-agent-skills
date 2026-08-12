# Eval: dns-resolution-failure

**Difficulty:** medium
**Branch:** ROOT_CAUSE_IDENTIFIED — private DNS is disabled on the interface endpoint; ec2.us-east-1.amazonaws.com resolves to public IP instead of endpoint ENI

## Prompt

Diagnose an interface VPC endpoint vpce-ec2dns111 for the EC2
service (com.amazonaws.us-east-1.ec2). The endpoint's security
group sg-ec2ep allows inbound TCP 443 from the full VPC CIDR.
Private DNS is disabled. Clients report that
ec2.us-east-1.amazonaws.com resolves to a public IP instead of
the endpoint. Endpoint policy is default. Endpoint state is
available.
