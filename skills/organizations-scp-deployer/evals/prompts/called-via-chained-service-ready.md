# Eval prompt: called-via-chained-service-ready

Plan the following SCP deployment using aws:CalledVia to scope
CloudFormation-driven IAM calls and emit the standard VERDICT block.

Operation: deploy-scp
Policy name: allow-iam-via-cloudformation
Strategy: guardrail
Target: ou-app-a
Policy goal: allow iam:CreateRole, iam:PassRole only when invoked
  via CloudFormation
Condition keys: aws:CalledVia

```json
{
  "OrgState": {
    "describe-organization": {
      "Organization.FeatureSet": "ALL_FEATURES"
    },
    "list-roots.PolicyTypes": [
      {"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}
    ],
    "list-organizational-units-for-parent.r-abc1": [
      {"Id": "ou-app-a", "Name": "app-a"}
    ],
    "caller_iam": {
      "role": "AWSOrgAdminRole",
      "permissions": ["organizations:CreatePolicy", "organizations:AttachPolicy"]
    }
  }
}
```
