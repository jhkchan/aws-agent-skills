# Eval prompt: policy-type-not-enabled-blocked

Plan the following Organizations SCP deployment and emit the standard
VERDICT block. The organization is in CONSOLIDATED_BILLING mode and
the SERVICE_CONTROL_POLICY type is not enabled on the root.

Operation: deploy-scp
Policy name: deny-root-user-actions
Strategy: guardrail
Target: r-abc1 (root)
Policy goal: deny root principal actions
Condition keys: aws:PrincipalType

```json
{
  "OrgState": {
    "describe-organization": {
      "Organization.FeatureSet": "CONSOLIDATED_BILLING"
    },
    "list-roots.PolicyTypes": [],
    "caller_iam": {
      "role": "AWSOrgAdminRole",
      "permissions": ["organizations:CreatePolicy", "organizations:AttachPolicy", "organizations:EnablePolicyType"]
    }
  }
}
```
