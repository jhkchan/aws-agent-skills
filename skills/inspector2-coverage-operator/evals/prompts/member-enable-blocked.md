# Eval prompt: member-enable-blocked

Plan the following Inspector enablement attempt and emit the
standard VERDICT block.

Operation: enable
Account: 333333333333 (member under org-mode)
Region: us-east-1
Resource types: EC2

```json
{
  "OrgModeCheck": {
    "describe-organization-configuration": {
      "autoEnable": {"ec2": true, "ecr": true, "lambda": true},
      "delegatedAdminAccountId": "222222222222",
      "maxAccountLimitReached": false
    },
    "list-members --only-associated": {
      "members": [
        {"accountId": "333333333333", "relationshipStatus": "ENABLED"}
      ]
    },
    "caller_iam": {
      "role": "MemberAccountOperatorRole",
      "caller_account": "333333333333",
      "permissions": ["inspector2:Enable"]
    }
  }
}
```
