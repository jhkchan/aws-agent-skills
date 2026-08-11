# Eval prompt: deploy-windows-auto-approve-ready

Plan the following SSM Patch Baseline creation and emit the standard
VERDICT block (BASELINE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, OPERATING_SYSTEM, APPROVAL_RULES, COMPLIANCE_LEVEL,
PATCH_GROUPS, MAINTENANCE_WINDOW, INSTANCE_ROLE, NOTES).

Operation: create
Baseline name: win-prod-critical
Region: us-east-1
Account: 111111111111
OperatingSystem: WINDOWS_SERVER
ApprovalRules:
  PatchRules:
    - PatchFilterGroup:
        OperatingSystem: WINDOWS_SERVER
        PatchFilters:
          - Key: PRODUCT, Values: ["WindowsServer2022"]
          - Key: CLASSIFICATION, Values: ["Critical Updates", "Security Updates"]
          - Key: MSRC_SEVERITY, Values: ["Critical"]
      ApproveAfterDays: 0
      ComplianceLevel: CRITICAL
      EnableNonSecurity: false
RejectedPatches: ["KB5012345"]
RejectedPatchesAction: BLOCK_AS_PENDING
Patch Group: win-prod-servers

```json
{
  "PreFlight": {
    "describe-patch-baselines": "no baseline named win-prod-critical",
    "ec2.describe-instances": "5 instances with Patch Group=win-prod-servers, all have AmazonSSMManagedInstanceCore",
    "iam.get-role.SSMOperatorRole": "OK"
  }
}
```
