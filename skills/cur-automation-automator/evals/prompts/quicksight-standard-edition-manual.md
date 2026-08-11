# Eval prompt: quicksight-standard-edition-manual

Add QuickSight to the existing CUR + Athena stack and emit the standard
VERDICT block.

Operation: add-quicksight
Stack name: prod-cur-quicksight
Caller: payer 111111111111
CUR + Athena already configured (verified)

```json
{
  "RequirementChecks": {
    "quicksight.describe-account": {
      "AccountEdition": "STANDARD"
    },
    "s3api.get-bucket-policy.prod-cur-bucket": {
      "Status": "OK"
    },
    "athena.list-work-groups": {
      "finops-cur": {
        "BytesScannedCutoffPerQuery": 1099511627776
      }
    }
  }
}
```
