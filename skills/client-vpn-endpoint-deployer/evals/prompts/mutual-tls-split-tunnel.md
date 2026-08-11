# Eval: mutual-tls-split-tunnel

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — mutual TLS auth, split-tunnel with custom DNS server (leak prevention), single subnet association, allow-all authorization rule

## Prompt

Create a Client VPN endpoint in us-east-1, account
123456789012. Client CIDR 10.250.0.0/16. Mutual TLS auth using
server certificate
arn:aws:acm:us-east-1:123456789012:certificate/abc123. Split
tunnel enabled. DNS server 10.0.0.2 (VPC resolver). Target VPC
vpc-aaa11122 (10.0.0.0/16). Associate subnet subnet-aaa11122 in
us-east-1a. Authorization rule: allow all groups to access
10.0.0.0/16. Connection logging to CloudWatch log group
client-vpn-logs. Transport UDP on port 443. Tags:
Environment=production, Access=corporate.
