# Eval: network-firewall-policy-remediation

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — NETWORK_FIREWALL, OU targeting, stateless+stateful rule groups, subnet mappings, auto-remediation with 14-day grace

## Prompt

Create an FMS Network Firewall policy named org-nfw-inspection
targeting OU ou-workloads-abcdef in us-east-1. FMS admin account
is 111111111111. Use stateless rule group rs-stateless-aaa and
stateful rule group rs-stateful-bbb. Firewall subnets are
subnet-aaa and subnet-bbb in each target account. Remediation
auto-apply with 14-day grace period. Policy priority 1.
