# Worked Examples — Multi-Account Governance Automator

## Worked example — MANUAL_STEP_REQUIRED (SCP gap)

```text
STRUCTURE:
  Org status: all-features
  OU depth: 1 (flat — all accounts under root)
  Foundational accounts: audit=none, log-archive=none
CONTROLS:
  - [FAIL] No root-level guardrail SCP
  - [FAIL] No SCP denies organizations:LeaveOrganization
  - [WARN] Sandbox account has same SCP scope as prod account
DELEGATION:
  - [FAIL] GuardDuty NOT delegated — running from management account
  - [FAIL] No Config aggregator
  - [PASS] CloudTrail org trail present
SHARING:
  - [FAIL] No IAM Identity Center
  - [FAIL] No break-glass path documented
VERDICT: MANUAL_STEP_REQUIRED
FINDINGS:
  - [CRITICAL] No deny-leave-org SCP: a compromised member can call
    organizations:LeaveOrganization to escape SCP governance entirely.
  - [CRITICAL] Flat OU: blast radius equals the management account for all 12 members.
  - [HIGH] GuardDuty in management account: couples security to the most privileged account.
REMEDIATION:
  1. Attach deny-leave-org + deny-root-actions SCP at the root.
  2. Create Security + Workloads-Prod + Workloads-NonProd + Sandbox OUs.
  3. Delegate GuardDuty + Security Hub + Config to a new audit account.
  4. Stand up IAM Identity Center; document a break-glass permission set.
```

