# Eval prompt: deploy-dns-firewall-ready

Plan the following DNS Firewall rule group deployment and emit the
standard VERDICT block (RESOLVER, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, ENDPOINT_TYPE, SUBNETS, SECURITY_GROUPS, FORWARDING_RULES,
FIREWALL_GROUPS, QUERY_LOGS, NOTES).

Operation: create
Region: us-east-1
Account: 111111111111
VPC: vpc-0abc123
Firewall rule group:
  Name: prod-firewall-rules
  Rules:
    - ManagedDomainListId: rslvr-fdl-aws-managed-domains-malware
      Priority: 1
      Action: BLOCK
      BlockResponse: NXDOMAIN
Association:
  VPC: vpc-0abc123
  Priority: 1
  MutationProtection: ENABLED

```json
{
  "PreFlight": {
    "list-firewall-rule-group-associations": "no associations on vpc-0abc123",
    "list-firewall-domain-lists": "rslvr-fdl-aws-managed-domains-malware exists",
    "iam.get-role.ResolverOperatorRole": "OK"
  }
}
```
