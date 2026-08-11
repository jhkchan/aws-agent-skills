# Eval: ad-connector-onprem-dns

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — AD Connector with on-prem DNS server IPs, VPN connectivity verified, SSO connected, AD Connector limitations (no trust, no LDAPS) respected

## Prompt

Create an AD Connector in us-east-1. VPC vpc-ccc33344 with
subnets subnet-ccc333 (us-east-1a) and subnet-ddd444 (us-east-1b).
On-prem AD DNS servers at 10.0.1.53 and 10.0.2.53 (reachable via
VPN). Connect IAM Identity Center SSO. Tags: Environment=staging,
ManagedBy=cloudops.
