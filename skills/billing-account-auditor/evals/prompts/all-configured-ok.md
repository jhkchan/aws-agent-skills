# Eval prompt: all-configured-ok

Audit the following AWS account billing configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Account id: 666666666666 (alias: all-configured-ok)
Account type: Standalone
Cost Explorer: Enabled
Billing configuration snapshot:
  Account-level IAM billing access: ACTIVATED
  AccountMFAEnabled: 1
  AccountAccessKeysPresent: 0
  IAM billing principals:
    - Group "FinOpsAdmins": aws-portal:ViewBilling, aws-portal:ModifyBilling, ce:*, budgets:*, cur:*
  Cost Anomaly Detection monitors: 1 (AllServicesMonitor, DIMENSIONAL)
  Cost Anomaly Detection subscriptions: 1 (threshold $100, IMMEDIATE)
  Billing budgets: 1 (MonthlyCostBudget, $5000, 80% and 100% ACTUAL alerts)
  Free-tier usage alerts: enabled
