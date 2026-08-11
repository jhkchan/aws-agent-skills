# Eval prompt: root-deny-cannot-be-overridden-blocked

The user wants to deny ec2:* at the org root and re-allow it at a
child OU (ou-prod-a). The intersection rule forbids this. Plan the
VERDICT block explaining the intersection rule and recommending the
correct pattern (OU-scoped Deny or condition keys).

Operation: deploy-scp
Requested: Deny ec2:* at root r-abc1, Allow ec2:* at ou-prod-a
Stated reason: "allow ec2 only in prod OU"

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
      {"Id": "ou-prod-a", "Name": "prod-a"}
    ],
    "caller_iam": {
      "role": "AWSOrgAdminRole",
      "permissions": ["organizations:CreatePolicy", "organizations:AttachPolicy"]
    }
  }
}
```
