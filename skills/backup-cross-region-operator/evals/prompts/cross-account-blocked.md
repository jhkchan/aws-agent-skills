# Eval prompt: cross-account-blocked

Plan the following AWS Backup cross-account copy attempt and emit
the standard VERDICT block.

Operation: cross-account-enable
Source account: 111111111111
Destination account: 222222222222
Region: us-east-1

```json
{
  "CrossAccountCheck": {
    "organizations.describe-organization": {
      "Id": "o-abc123",
      "ManagementAccountId": "999999999999"
    },
    "organizations.list-accounts": {
      "accounts": [
        {"Id": "999999999999", "Name": "mgmt"},
        {"Id": "111111111111", "Name": "source-member"}
      ],
      "destination_in_org": false
    },
    "organizations.describe-effective-policy.BACKUP_POLICY": {
      "policy_document": null
    },
    "caller_iam": {
      "role": "OrgsManagementRole",
      "permissions": ["organizations:DescribeEffectivePolicy",
                      "organizations:DescribeOrganization"]
    }
  }
}
```
