# Eval prompt: deploy-patch-group-maintenance-window-ready

Plan the following maintenance window integration and emit the standard
VERDICT block (BASELINE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, OPERATING_SYSTEM, APPROVAL_RULES, COMPLIANCE_LEVEL,
PATCH_GROUPS, MAINTENANCE_WINDOW, INSTANCE_ROLE, NOTES).

Operation: maintenance-window-integration
Region: us-east-1
Account: 111111111111
Baseline ID: pb-0abc123 (al2023-prod-security, already created)
Patch Group: al2023-prod-web
Maintenance Window:
  WindowId: mw-0abc123
  Operation: Install
  MaxConcurrency: "10%"
  MaxErrors: "3"
  ServiceRoleArn: arn:aws:iam::111111111111:role/MaintenanceWindowRole

```json
{
  "PreFlight": {
    "describe-maintenance-windows.mw-0abc123": "OK (exists, schedule cron(0 2 ? * SUN *))",
    "iam.get-role.MaintenanceWindowRole": "OK (trusts ssm.amazonaws.com, has ssm:SendCommand)",
    "iam.get-role.SSMOperatorRole": "OK"
  }
}
```
