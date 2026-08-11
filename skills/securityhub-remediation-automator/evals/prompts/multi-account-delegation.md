# Eval prompt: multi-account-delegation

Design a multi-account Security Hub remediation setup using Organizations
delegated administrator. Emit the standard REMEDIATION block (FINDING_TYPE,
STANDARD, SEVERITY_ROUTE, RUNBOOK, TRIGGER, SAFETY, SUPPRESSION, VERDICT,
TEMPLATE).

Design reference: multi-account-delegation
Organizations: 5 member accounts
Delegated admin account: 222222222222
Region: us-east-1

Requirements:
- Designate 222222222222 as delegated administrator for Security Hub
- Invite 5 member accounts (333333333333 through 777777777777)
- Enable FSBP standard for all members
- Configure EventBridge rule on delegated admin for aggregated findings
- Set up a Lambda dispatcher that routes CRITICAL/HIGH findings to SSM runbooks
