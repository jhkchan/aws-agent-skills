# Eval prompt: linked-account-caller-manual

Design a CUR automation stack and emit the standard VERDICT block.

Operation: create
Stack name: linked-account-cur
Caller: linked account 222222222222
Payer account: 111111111111
Goal: organization-wide FinOps dashboards

```json
{
  "RequirementChecks": {
    "organizations.describe-organization": {
      "MasterAccountId": "111111111111"
    },
    "sts.get-caller-identity": {
      "Account": "222222222222"
    },
    "cur.describe-report-definitions": {
      "Error": "AccessDenied"
    }
  }
}
```
