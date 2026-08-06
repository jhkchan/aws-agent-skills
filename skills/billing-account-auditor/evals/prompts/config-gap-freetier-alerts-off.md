# Eval prompt: config-gap-freetier-alerts-off

Audit the following AWS account billing configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Account id: 555555555555 (alias: config-gap-freetier-alerts-off)
Account type: Standalone
Cost Explorer: Enabled
Billing configuration snapshot:
  Account-level IAM billing access: ACTIVATED
  AccountMFAEnabled: 1
  AccountAccessKeysPresent: 0
  IAM billing principals:
    - Group "FinOpsViewers": aws-portal:ViewBilling, ce:GetCostAndUsage, budgets:ViewBudget
  Cost Anomaly Detection monitors: 1 (AllServicesMonitor, DIMENSIONAL)
  Cost Anomaly Detection subscriptions: 1 (threshold $100, IMMEDIATE)
  Billing budgets: 1 (MonthlyCostBudget, $2000, 50%, 80%, 100% ACTUAL alerts)
  Free-tier usage alerts: not enabled
