# Eval prompt: guardrail-deny-regions-ready

Plan the following Organizations SCP deployment and emit the standard
VERDICT block (POLICY_SPEC, VERDICT, ARCHITECTURE, CHECKLIST,
FINDINGS, DEPLOY_COMMANDS).

Operation: deploy-scp
Policy name: deny-unapproved-regions
Strategy: guardrail
Target: r-abc1 (root)
Policy goal: deny regions outside us-east-1, eu-west-1, us-west-2
Condition keys: aws:RequestedRegion

```json
{
  "OrgState": {
    "describe-organization": {
      "Organization.FeatureSet": "ALL_FEATURES"
    },
    "list-roots.PolicyTypes": [
      {"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}
    ],
    "list-policies-for-target.r-abc1": [
      {"Name": "FullAWSAccess", "AwsManaged": true}
    ],
    "caller_iam": {
      "role": "AWSOrgAdminRole",
      "permissions": ["organizations:CreatePolicy", "organizations:AttachPolicy"]
    }
  }
}
```
