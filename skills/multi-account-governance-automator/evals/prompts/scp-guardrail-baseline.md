# Eval prompt: scp-guardrail-baseline

Design a root-level SCP guardrail baseline for our existing AWS
organization. Emit the standard GOVERNANCE block.

Requirements:
- Org: all-features, 30 member accounts, currently no SCPs attached
- SCPs to create and attach at the root:
  1. Deny organizations:LeaveOrganization (prevent escape from SCP governance)
  2. Deny root-account actions except iam:CreateVirtualMFADevice,
     iam:EnableRootMFA, iam:Get*, iam:List*
  3. Deny guardduty:DeleteDetector + guardduty:UpdateDetector +
     guardduty:DisassociateFromMasterAccount
  4. Deny cloudtrail:DeleteTrail + cloudtrail:StopLogging +
     cloudtrail:UpdateTrail
- Attach at root so all 30 member accounts inherit
- Management account MFA: yes (virtual MFA, no access keys)
- Dry-run tested on sandbox account before root attachment via IAM Policy
  Simulator
- SCP inheritance reviewed: Deny at root applies to all members; Deny
  always wins over any future Allow at child OUs

Expected: AUTOMATED. The guardrail baseline covers the mandatory
preventive controls (deny-leave-org, deny-root-actions, deny-disable-
guardduty, deny-delete-cloudtrail) with correct attachment at root and
a documented inheritance review.
