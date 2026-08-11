# Eval: authorization-rule-ordering

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — multiple authorization rules ordered specific-first, broad-last (first-match wins)

## Prompt

Create a Client VPN endpoint in us-east-1, account
123456789012. Client CIDR 10.250.0.0/16. Mutual TLS auth using
server certificate
arn:aws:acm:us-east-1:123456789012:certificate/abc123. Split
tunnel enabled. DNS server 10.0.0.2. Target VPC vpc-aaa11122
(10.0.0.0/16). Associate subnet subnet-aaa11122. Create TWO
authorization rules: (1) allow group data-team to access
10.0.0.0/16, (2) allow all groups to access 0.0.0.0/0. Rule 1
must be evaluated before rule 2. Tags: Environment=production,
Access=multi-rule.
