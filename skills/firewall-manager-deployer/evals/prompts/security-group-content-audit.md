# Eval: security-group-content-audit

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SECURITY_GROUPS_CONTENT_AUDIT, account-level targeting, monitor-only (RemediationEnabled=false), safe rollout

## Prompt

Create an FMS security group policy named org-sg-audit-no-ssh-open
targeting accounts 111111111111 and 222222222222 in us-east-1.
FMS admin account is 000000000000. Use content audit mode to
check that no security group has port 22 open to 0.0.0.0/0.
Start in monitor-only mode (RemediationEnabled=false) for safe
rollout. Policy priority 2.
