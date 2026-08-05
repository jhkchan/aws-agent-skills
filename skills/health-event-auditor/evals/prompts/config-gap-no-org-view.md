# Eval prompt: config-gap-no-org-view

Audit the following AWS account posture for Health configuration gaps.
Emit the standard VERDICT block (ACCOUNT/SCOPE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account posture:
  Support plan: Business
  AWS Region (API endpoint): us-east-1
  AWS Organization: present (management account 111111111111,
    12 member accounts)
  Health Organizational View:
    healthServiceAccessStatusForOrganization: disabled
  EventBridge rule for aws.health: present (default-rule-Health-...)

No specific event provided; the auditor is reviewing overall Health
posture across the organization.
