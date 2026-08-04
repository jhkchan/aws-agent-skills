# Eval prompt: no-anomaly-detection

Audit the following AWS account billing configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Account id: 333333333333 (alias: no-anomaly-detection)
Account type: Standalone
Cost Explorer: Enabled
Billing configuration snapshot:
  Account-level IAM billing access: ACTIVATED
  AccountMFAEnabled: 1
  AccountAccessKeysPresent: 0
  IAM billing principals:
    - Group "FinOpsAdmins": aws-portal:ViewBilling, aws-portal:ModifyBilling, ce:*, budgets:*, cur:*
  Cost Anomaly Detection monitors: none
  Cost Anomaly Detection subscriptions: none
  Billing budgets: 1 (MonthlyTotal, $3000, 80% and 100% ACTUAL alerts)
  Free-tier usage alerts: enabled
