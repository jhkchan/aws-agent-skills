# Eval prompt: missing-bucket-policy-manual

Create a CUR automation stack and emit the standard VERDICT block.

Operation: create
Stack name: prod-cur-stack
Caller: payer 111111111111
CUR bucket: prod-cur-bucket (us-east-1, exists)

```json
{
  "RequirementChecks": {
    "organizations.describe-organization": {
      "MasterAccountId": "111111111111"
    },
    "s3api.get-bucket-location.prod-cur-bucket": {
      "LocationConstraint": "us-east-1"
    },
    "s3api.get-bucket-policy.prod-cur-bucket": {
      "Statement[0].Principal.Service": "billingreports.amazonaws.com",
      "MissingPrincipal": "athena.amazonaws.com"
    },
    "glue.get-database.prod_cur": {
      "Status": "EntityNotFoundException"
    }
  }
}
```
