# Eval: network-reachability-sg-overly-permissive

**Difficulty:** medium
**Branch:** ROOT_CAUSE_FOUND — SG_OVERLY_PERMISSIVE layer, remediation is SG restrict (not package patch)

## Prompt

Inspector fired a CRITICAL NETWORK_REACHABILITY finding on EC2
instance i-db99 (us-east-1, account 123456789012). Port 3306 TCP
is reachable from CIDR 0.0.0.0/0, scope INTERNET. Security group
sg-db1 has an inbound rule 0.0.0.0/0 on tcp/3306. The instance
has a public IP (203.0.113.10). lastObservedAt 2026-08-09T22:00Z.
No package CVEs on the instance. How do I remediate?
