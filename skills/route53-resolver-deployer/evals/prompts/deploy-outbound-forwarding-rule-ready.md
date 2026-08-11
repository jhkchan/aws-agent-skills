# Eval prompt: deploy-outbound-forwarding-rule-ready

Plan the following Route 53 Resolver outbound endpoint + forwarding rule
deployment and emit the standard VERDICT block (RESOLVER, VERDICT,
TARGET, PRE_CHECKS, STEPS, POST_VERIFY, ENDPOINT_TYPE, SUBNETS,
SECURITY_GROUPS, FORWARDING_RULES, FIREWALL_GROUPS, QUERY_LOGS, NOTES).

Operation: create
Endpoint name: prod-outbound
Region: us-east-1
Account: 111111111111
Direction: OUTBOUND
VPC: vpc-0abc123 (enableDnsSupport=true, enableDnsHostnames=true)
SecurityGroupId: sg-0def456 (egress UDP/TCP 53 to 10.99.1.5, 10.99.2.5)
IpAddresses:
  - SubnetId: subnet-aaa (us-east-1a)
  - SubnetId: subnet-bbb (us-east-1b)
Forwarding rule:
  Name: forward-corp-local
  DomainName: corp.example.local.
  TargetIps: [{"Ip":"10.99.1.5","Port":53},{"Ip":"10.99.2.5","Port":53}]

```json
{
  "PreFlight": {
    "list-resolver-endpoints": "no endpoint named prod-outbound",
    "ec2.describe-security-groups.sg-0def456": "egress 10.99.1.5/32, 10.99.2.5/32 UDP/TCP 53",
    "list-resolver-rules": "no rule for corp.example.local.",
    "iam.get-role.ResolverOperatorRole": "OK"
  }
}
```
