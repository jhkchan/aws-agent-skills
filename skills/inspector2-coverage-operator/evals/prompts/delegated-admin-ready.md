# Eval prompt: delegated-admin-ready

Plan the following Inspector delegated admin enablement and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, STATE, NOTES).

Operation: enable-delegated-admin
Management account (caller): 111111111111
Target delegated admin: 222222222222
Region: us-east-1

```json
{
  "DelegatedAdminCheck": {
    "list-delegated-admin-accounts": {
      "delegatedAdmins": []
    },
    "organizations.describe-organization": {
      "OrganizationId": "o-abc123def456",
      "ManagementAccountId": "111111111111"
    },
    "organizations.list-roots": {
      "roots": [{"id": "r-abc", "name": "Root"}],
      "accounts_in_root": ["111111111111", "222222222222"]
    },
    "caller_iam": {
      "role": "OrgsManagementRole",
      "permissions": ["inspector2:EnableDelegatedAdminAccount",
                      "organizations:EnableAWSServiceAccess"]
    }
  }
}
```
