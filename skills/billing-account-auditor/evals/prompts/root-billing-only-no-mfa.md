# Eval prompt: root-billing-only-no-mfa

Audit the following AWS account billing configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Account id: 111111111111 (alias: root-billing-only-no-mfa)
Account type: Standalone
Cost Explorer: Enabled
Billing configuration snapshot:
  Account-level IAM billing access: DEACTIVATED
  AccountMFAEnabled: 0
  AccountAccessKeysPresent: 0
  IAM billing principals: none (no user/group/role has aws-portal:*, ce:*, cur:*, budgets:*)
  Cost Anomaly Detection monitors: none
  Cost Anomaly Detection subscriptions: none
  Billing budgets: none
  Free-tier usage alerts: not enabled
