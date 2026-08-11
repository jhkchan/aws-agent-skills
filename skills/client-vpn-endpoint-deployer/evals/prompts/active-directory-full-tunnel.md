# Eval: active-directory-full-tunnel

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Active Directory auth (AWS Managed AD), full-tunnel mode, group-restricted authorization rule

## Prompt

Create a Client VPN endpoint in us-east-1, account
123456789012. Client CIDR 10.251.0.0/16. Active Directory
authentication using directory ID d-9067a4a4bd (AWS Managed
Microsoft AD). Server certificate
arn:aws:acm:us-east-1:123456789012:certificate/abc123. Full
tunnel (no split-tunnel). DNS server 10.0.0.2. Target VPC
vpc-bbb22233 (172.16.0.0/16). Associate subnet subnet-bbb22233
in us-east-1b. Authorization rule: allow group "corp-users" to
access 172.16.0.0/16. Connection logging to CloudWatch log
group client-vpn-ad-logs. Tags: Environment=production,
Auth=active-directory.
