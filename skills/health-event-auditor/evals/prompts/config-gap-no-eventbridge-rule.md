# Eval prompt: config-gap-no-eventbridge-rule

Audit the following AWS account posture for Health configuration gaps.
Emit the standard VERDICT block (ACCOUNT/SCOPE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account posture:
  Support plan: Business
  AWS Region (API endpoint): us-east-1
  Health Organizational View: enabled
  EventBridge rules matching source aws.health: NONE
  Default event bus policy authorizes health.amazonaws.com: true

Active events (status=open, upcoming): none in the last 24h.
