# End-to-end usage scenario: billing-account-auditor

A walkthrough showing the skill auditing an AWS account that has root
access keys (CRITICAL — MFA-bypassing billing backdoor) despite otherwise
solid billing configuration, demonstrating how the worst finding drives
the verdict and why root access keys trump every other dimension.

## Input (user prompt)

> Audit the billing posture of this account before our FinOps compliance
> review next week. We think everything is set up but want a verdict.

```text
Account id: 222222222222
Account type: Standalone
Cost Explorer: Enabled
Billing configuration snapshot:
  Account-level IAM billing access: ACTIVATED
  AccountMFAEnabled: 1
  AccountAccessKeysPresent: 1
  IAM billing principals:
    - Group "FinOpsViewers": aws-portal:ViewBilling, ce:GetCostAndUsage, budgets:ViewBudget
  Cost Anomaly Detection monitors: 1 (AllServicesMonitor, DIMENSIONAL)
  Cost Anomaly Detection subscriptions: 1 (threshold $100, IMMEDIATE)
  Billing budgets: 1 (MonthlyCostBudget, $5000, 80% ACTUAL alert)
  Free-tier usage alerts: enabled
```

## Skill output

```text
ACCOUNT: 222222222222
VERDICT: ROOT_BILLING
RISK: CRITICAL
REASON: Root account has active access keys (AccountAccessKeysPresent: 1) —
a permanent MFA-bypassing billing backdoor that grants unlimited programmatic
billing API access (Step 1). All other dimensions are properly configured.
FINDINGS:
  - [CRITICAL] Root access keys present — API access to all billing actions
    (aws-portal:*, ce:*, budgets:*, cur:*) without MFA (Step 1)
  - [OK] Root MFA is enabled (AccountMFAEnabled: 1) (Step 1)
  - [OK] IAM billing access is ACTIVATED with delegated principals (Step 2)
  - [OK] Cost Anomaly Detection enabled with monitor + subscription (Step 3)
  - [OK] Billing budget configured with 80% ACTUAL alert (Step 4)
  - [OK] Free-tier usage alerts enabled (Step 5)
REMEDIATION:
  1. CRITICAL — Sign in to the console as root and delete the access key.
     This is the ONLY way to manage root keys — IAM admins cannot do this
     via CLI. The root access key cannot be deleted programmatically by
     any IAM user, even AdministratorAccess.
  2. Audit CloudTrail for API calls from the root access key
     (userIdentity.type: "Root") during the exposure window. Focus on
     billing API calls: aws-portal:*, budgets:*, ce:*, cur:*.
  3. If the key was used to modify billing settings, review and revert
     any unauthorized changes.
```

## What the skill caught that a generic assistant misses

1. **Root access keys bypass MFA entirely.** A generic assistant says
   "you should delete the root access keys." The skill explains WHY this
   is CRITICAL: the access key authenticates API calls with no second
   factor, giving unlimited programmatic billing access including account
   closure. Root MFA being enabled (which it is) is irrelevant for API
   calls made with the access key — MFA only protects console sign-in.

2. **The worst finding trumps everything else.** Every other dimension is
   perfectly configured — IAM delegation active, CAD with subscriptions,
   budgets with alerts, free-tier alerts on. A generic assistant might
   call this "mostly fine." The skill's ordered classification correctly
   produces ROOT_BILLING because root access keys are a CRITICAL finding
   that dominates the verdict regardless of other dimensions.

3. **Root key deletion is root-only.** A generic assistant might suggest
   `aws iam delete-access-key --access-key-id <AKIA...>`. The skill
   correctly identifies that root keys can only be managed by signing in
   as root in the console — no IAM user, not even AdministratorAccess,
   can delete root keys via CLI. This is a critical remediation detail.

4. **CloudTrail forensic scope.** The skill specifies searching for
   `userIdentity.type: "Root"` and focusing on billing API calls during
   the exposure window — the attack surface of a root key is billing-
   specific (account closure, payment-method changes, budget tampering).

## Slash-command invocation

```
/aws:audit-billing-account
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit billing posture before the FinOps review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: billing-account-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit my billing configuration"
# [Phase: Audit | Skills routed: billing-account-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the root access keys, validate the full posture:

```bash
# Verify root access keys are gone
aws iam get-account-summary --profile default \
  --query 'SummaryMap.AccountAccessKeysPresent'
# Expected: 0

# Verify root MFA
aws iam get-account-summary --profile default \
  --query 'SummaryMap.AccountMFAEnabled'
# Expected: 1

# Confirm CAD monitors exist
aws ce list-cost-anomaly-monitors --profile default --region us-east-1

# Confirm budgets exist with notifications
aws budgets describe-budgets --account-id 222222222222 --profile default
aws budgets describe-notifications-for-budget \
  --account-id 222222222222 --budget-name MonthlyCostBudget \
  --profile default
```

Then monitor CloudTrail for any `userIdentity.type: "Root"` billing API
calls for 1-2 weeks to confirm no residual unauthorized activity.
