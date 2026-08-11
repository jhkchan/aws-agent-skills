# Eval: saml-federation-self-service-portal

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SAML 2.0 federation auth, self-service portal enabled, full-tunnel mode

## Prompt

Create a Client VPN endpoint in us-east-1, account
123456789012. Client CIDR 10.250.0.0/16. SAML federated
authentication using provider
arn:aws:iam::123456789012:saml-provider/CorporateIdP. Server
certificate arn:aws:acm:us-east-1:123456789012:certificate/abc123
(required even for SAML). Enable self-service portal. Full-tunnel
mode. DNS server 10.0.0.2. Target VPC vpc-aaa11122
(10.0.0.0/16). Associate subnet subnet-aaa11122. Authorization
rule: allow all groups to access 10.0.0.0/16. Tags:
Environment=production, Auth=federated.
