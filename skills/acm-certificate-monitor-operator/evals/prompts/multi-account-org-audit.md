# Eval: multi-account-org-audit

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — audit of all ACM certs across 5 Organization accounts using assume-role, scanning us-east-1 and eu-west-1

## Prompt

Audit all ACM certificates across my Organization. I have 5
accounts: 111111111111 (audit account), 222222222222 (prod),
333333333333 (staging), 444444444444 (dev), 555555555555 (shared).
Use the ACMMonitoringRole in each member account to assume
access. Scan us-east-1 and eu-west-1. List all certificates
with status, renewal eligibility, and flag any unattached
certificates or renewal failures. The audit account
(111111111111) runs the audit.
