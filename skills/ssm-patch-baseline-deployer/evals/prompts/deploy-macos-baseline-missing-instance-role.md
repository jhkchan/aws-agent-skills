# Eval prompt: deploy-macos-baseline-missing-instance-role

Plan the following SSM Patch Baseline creation and emit the standard
VERDICT block (BASELINE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, OPERATING_SYSTEM, APPROVAL_RULES, COMPLIANCE_LEVEL,
PATCH_GROUPS, MAINTENANCE_WINDOW, INSTANCE_ROLE, NOTES).

Operation: create
Baseline name: macos-prod-baseline
Region: us-east-1
Account: 111111111111
OperatingSystem: MACOS
ApprovalRules:
  PatchRules:
    - PatchFilterGroup:
        OperatingSystem: MACOS
        PatchFilters:
          - Key: PRODUCT, Values: ["macOS"]
          - Key: CLASSIFICATION, Values: ["Security"]
      ApproveAfterDays: 3
      ComplianceLevel: HIGH
Patch Group: macos-prod-fleet

```json
{
  "PreFlight": {
    "describe-patch-baselines": "no baseline named macos-prod-baseline",
    "ec2.describe-instances": "2 instances with Patch Group=macos-prod-fleet, instance profiles do NOT include AmazonSSMManagedInstanceCore",
    "iam.get-role.SSMOperatorRole": "OK"
  }
}
```
