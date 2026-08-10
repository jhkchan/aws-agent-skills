# Eval prompt: cross-account-route53-access-denied-blocked

Diagnose the following Route 53 cross-account scenario and emit the
standard VERDICT block.

Operation: diagnose-failover
FQDN: api.example.com
Hosted zone: Z2ABCDEFGHIJK (in account 111111111111 / account A)
Operator: role in account 222222222222 / account B

```json
{
  "OperatorLastAttempt": {
    "command": "aws route53 change-resource-record-sets --hosted-zone-id Z2ABCDEFGHIJK --change-batch ...",
    "result": "AccessDeniedException — User: arn:aws:iam::222222222222:role/AppOpsRole is not authorized to perform: route53:ChangeResourceRecordSets on resource: arn:aws:route53:::hostedzone/Z2ABCDEFGHIJK"
  },
  "OperatorIdentityBasedPolicy": {
    "account_B": "Allows route53:* on * (verified)"
  },
  "ZoneOwningAccount": {
    "RAM_resource_share": "None for Z2ABCDEFGHIJK with account B",
    "Inline_policy_on_account_B_role": "None"
  },
  "RecordSetsViaBreakGlassRole": [
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"primary",
     "Failover":"PRIMARY","Value":"10.0.0.10","HealthCheckId":"h-primary","Status":"Healthy"},
    {"Name":"api.example.com.","Type":"A","SetIdentifier":"secondary",
     "Failover":"SECONDARY","Value":"10.0.1.10"}
  ]
}
```
