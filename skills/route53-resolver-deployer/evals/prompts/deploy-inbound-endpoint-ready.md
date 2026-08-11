# Eval prompt: deploy-inbound-endpoint-ready

Plan the following Route 53 Resolver inbound endpoint creation and emit
the standard VERDICT block (RESOLVER, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, ENDPOINT_TYPE, SUBNETS, SECURITY_GROUPS,
FORWARDING_RULES, FIREWALL_GROUPS, QUERY_LOGS, NOTES).

Operation: create
Endpoint name: prod-inbound
Region: us-east-1
Account: 111111111111
Direction: INBOUND
VPC: vpc-0abc123 (enableDnsSupport=true, enableDnsHostnames=true)
SecurityGroupId: sg-0abc123 (ingress UDP/TCP 53 from 10.99.0.0/16)
IpAddresses:
  - SubnetId: subnet-aaa (us-east-1a, 10.0.1.0/24), Ip: 10.0.1.10
  - SubnetId: subnet-bbb (us-east-1b, 10.0.2.0/24), Ip: 10.0.2.10

```json
{
  "PreFlight": {
    "list-resolver-endpoints": "no endpoint named prod-inbound",
    "ec2.describe-security-groups.sg-0abc123": "ingress 10.99.0.0/16 UDP/TCP 53",
    "iam.get-role.ResolverOperatorRole": "OK"
  }
}
```
