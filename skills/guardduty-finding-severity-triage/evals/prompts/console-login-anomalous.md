# Eval: console-login-anomalous

**Expected verdict:** MEDIUM
**Difficulty:** easy
**Branch:** Step 4 — behavioral anomaly (no FP override, no escalation)

## Prompt

Triage this GuardDuty finding. Emit the standard VERDICT block (FINDING,
VERDICT, REASON, REMEDIATION).

```
Finding name: console-login-anomalous
Finding type: UnauthorizedAccess:IAMUser/ConsoleLoginFromAnomalousLocation
Severity: 5.0
Title: Console login from an anomalous location
Description: IAM user jacky.chan logged into the AWS console from a location not previously associated with this user.
Resource type: IAMUser
Resource: AIDACKCEVSQ6C2EXAMPLE (jacky.chan)
Action type: AWS_API_CALL
Login location: Lagos, Nigeria (user's usual locations: Singapore, Hong Kong)
IP address: 105.112.0.55
MFA used: Yes
Count: 1
Confidence: MEDIUM
Context: No documented change window, travel request, or DR drill.
User has not reported travel to Nigeria.
```
