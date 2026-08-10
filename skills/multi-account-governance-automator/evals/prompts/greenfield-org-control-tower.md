# Eval prompt: greenfield-org-control-tower

Design a multi-account governance baseline for our greenfield AWS
organization. Emit the standard GOVERNANCE block (STRUCTURE, CONTROLS,
DELEGATION, SHARING, VERDICT, FINDINGS, REMEDIATION).

Requirements:
- Intent: new org
- Account count target: 50
- Compliance framework: PCI
- Landing surface: Control Tower Landing Zone v2
- OU hierarchy: Security (audit, log-archive), Infrastructure,
  Workloads-Prod, Workloads-NonProd, Sandbox, Suspended
- SCPs: deny-leave-org + deny-root-actions at root;
  region throttle at Workloads-Prod (us-east-1, eu-west-1 only);
  Deny-list at Sandbox (blocks QLDB, Macie2, AlexaForBusiness)
- Delegation: GuardDuty + Security Hub (CIS + Foundational) + Config
  (org source, AllRegions) + Access Analyzer to audit account 111111111111
- CloudTrail org trail delivering to log-archive account 222222222222
  S3 bucket org-trail-logs-2222 with KMS encryption; bucket policy uses
  aws:PrincipalOrgID condition
- IAM Identity Center: AWSAdministratorAccess (1h) +
  AWSReadOnlyAccess (4h) + EmergencyAdmin break-glass (sealed envelope,
  tested 2026-07-15)
- Resource Explorer: aggregator index in audit account, view
  CrossAccountView
- RAM shares: scoped to org (allow-external-principals=false)
- Management account MFA: yes (virtual MFA, no access keys)

Expected: AUTOMATED. The design covers all four layers (structure,
controls, delegation, visibility) plus sharing, with a documented SCP
inheritance order, tested landing-zone deployment, scoped delegated-admin
roles, and aggregation coverage across every member account.
