# Eval prompt: deploy-al2023-wrong-product-filter-blocked

Plan the following SSM Patch Baseline creation and emit the standard
VERDICT block (BASELINE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, OPERATING_SYSTEM, APPROVAL_RULES, COMPLIANCE_LEVEL,
PATCH_GROUPS, MAINTENANCE_WINDOW, INSTANCE_ROLE, NOTES).

Operation: create
Baseline name: al2023-prod-security
Region: us-east-1
Account: 111111111111
OperatingSystem: AMAZON_LINUX_2023
ApprovalRules:
  PatchRules:
    - PatchFilterGroup:
        OperatingSystem: AMAZON_LINUX_2023
        PatchFilters:
          - Key: PRODUCT, Values: ["Amazon Linux 2"]
          - Key: CLASSIFICATION, Values: ["Security"]
      ApproveAfterDays: 7
      ComplianceLevel: CRITICAL
Patch Group: al2023-prod-web

```json
{
  "PreFlight": {
    "describe-patch-baselines": "no baseline named al2023-prod-security",
    "ec2.describe-instances": "3 instances with Patch Group=al2023-prod-web, all have AmazonSSMManagedInstanceCore",
    "iam.get-role.SSMOperatorRole": "OK"
  }
}
```
