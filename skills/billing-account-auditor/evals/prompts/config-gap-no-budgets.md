# Eval prompt: config-gap-no-budgets

Audit the following AWS account billing configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Account id: 444444444444 (alias: config-gap-no-budgets)
Account type: Standalone
Cost Explorer: Enabled
Billing configuration snapshot:
  Account-level IAM billing access: ACTIVATED
  AccountMFAEnabled: 1
  AccountAccessKeysPresent: 0
  IAM billing principals:
    - Group "BillingAdmins": aws-portal:ViewBilling, ce:GetCostAndUsage, budgets:ViewBudget
  Cost Anomaly Detection monitors: 1 (AllServicesMonitor, DIMENSIONAL)
  Cost Anomaly Detection subscriptions: 1 (threshold $50, IMMEDIATE)
  Billing budgets: none
  Free-tier usage alerts: enabled
