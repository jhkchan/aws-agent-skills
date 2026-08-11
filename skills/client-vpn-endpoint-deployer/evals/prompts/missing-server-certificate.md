# Eval: missing-server-certificate

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — mutual TLS requires a server certificate in ACM; none provided

## Prompt

Create a Client VPN endpoint in us-east-1, account
123456789012. Client CIDR 10.250.0.0/16. Mutual TLS auth but no
server certificate has been imported into ACM yet. Target VPC
vpc-aaa11122 (10.0.0.0/16). Associate subnet subnet-aaa11122.
