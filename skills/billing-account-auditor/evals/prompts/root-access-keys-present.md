# Eval prompt: root-access-keys-present

Audit the following AWS account billing configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Account id: 222222222222 (alias: root-access-keys-present)
Account type: Standalone
Cost Explorer: Enabled
Billing configuration snapshot:
  Account-level IAM billing access: ACTIVATED
  AccountMFAEnabled: 1
  AccountAccessKeysPresent: 1
  IAM billing principals:
    - Group "FinOpsViewers": aws-portal:ViewBilling, ce:GetCostAndUsage, budgets:ViewBudget
  Cost Anomaly Detection monitors: 1 (AllServicesMonitor, DIMENSIONAL)
  Cost Anomaly Detection subscriptions: 1 (threshold $100, IMMEDIATE)
  Billing budgets: 1 (MonthlyCostBudget, $5000, 80% ACTUAL alert)
  Free-tier usage alerts: enabled
