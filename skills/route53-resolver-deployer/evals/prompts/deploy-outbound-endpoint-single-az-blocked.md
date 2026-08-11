# Eval prompt: deploy-outbound-endpoint-single-az-blocked

Plan the following Route 53 Resolver outbound endpoint deployment and
emit the standard VERDICT block (RESOLVER, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, ENDPOINT_TYPE, SUBNETS, SECURITY_GROUPS,
FORWARDING_RULES, FIREWALL_GROUPS, QUERY_LOGS, NOTES).

Operation: create
Endpoint name: prod-outbound
Region: us-east-1
Account: 111111111111
Direction: OUTBOUND
VPC: vpc-0abc123
SecurityGroupId: sg-0def456
IpAddresses:
  - SubnetId: subnet-aaa (us-east-1a)
  - SubnetId: subnet-ccc (us-east-1a — same AZ as subnet-aaa)

```json
{
  "PreFlight": {
    "list-resolver-endpoints": "no endpoint named prod-outbound",
    "ec2.describe-subnets": "subnet-aaa and subnet-ccc both in us-east-1a",
    "iam.get-role.ResolverOperatorRole": "OK"
  }
}
```
