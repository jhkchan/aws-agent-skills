# Eval prompt: deploy-query-log-missing-resource-policy

Plan the following Resolver query logging configuration and emit the
standard VERDICT block (RESOLVER, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, ENDPOINT_TYPE, SUBNETS, SECURITY_GROUPS, FORWARDING_RULES,
FIREWALL_GROUPS, QUERY_LOGS, NOTES).

Operation: create
Region: us-east-1
Account: 111111111111
VPC: vpc-0abc123
Query log config:
  Name: prod-query-logs-cw
  Destination: CloudWatch Logs
  DestinationArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/route53resolver/prod

```json
{
  "PreFlight": {
    "logs.describe-log-groups": "log group /aws/route53resolver/prod exists",
    "logs.describe-resource-policies": "no policy granting route53resolver.amazonaws.com logs:PutLogEvents",
    "list-resolver-query-log-configs": "no config named prod-query-logs-cw",
    "iam.get-role.ResolverOperatorRole": "OK"
  }
}
```
