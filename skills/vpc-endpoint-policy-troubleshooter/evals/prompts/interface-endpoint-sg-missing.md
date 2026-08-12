# Eval: interface-endpoint-sg-missing

**Difficulty:** hard
**Branch:** ROOT_CAUSE_IDENTIFIED — interface endpoint SG allows port 443 from 10.0.0.0/16 and 10.0.1.0/24 but NOT 10.0.2.0/24; clients in 10.0.2.0/24 get connection timeout

## Prompt

Troubleshoot a VPC interface endpoint vpce-aaa111222 for the
SSM service (com.amazonaws.us-east-1.ssm). Clients in subnet
10.0.2.0/24 are getting connection timeouts. The endpoint's
security group sg-vpce123 currently allows inbound TCP 443 from
10.0.0.0/16 and 10.0.1.0/24 only. Private DNS is enabled.
Endpoint policy is default (full access). Endpoint state is
available.
