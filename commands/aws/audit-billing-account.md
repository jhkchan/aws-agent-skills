---
description: Audit AWS account billing posture — root MFA and access keys, IAM user/group billing access delegation, Cost Anomaly Detection, billing budgets, and free-tier usage alerts.
nl_triggers:
  - "audit my billing configuration"
  - "check billing access"
  - "billing posture audit"
  - "is Cost Anomaly Detection enabled"
  - "do I have billing budgets"
  - "is root MFA enabled"
  - "billing alerts configured"
  - "free tier usage alerts"
  - "who can access billing"
  - "root account billing access"
  - "root access keys"
  - "IAM billing delegation"
  - "FinOps audit"
  - "billing preferences"
  - "cost governance check"
routes_to: billing-account-auditor
---

# /aws:audit-billing-account

Activate the `billing-account-auditor` skill and audit an AWS account's
billing posture across five dimensions.

## What it does

Reads a billing configuration snapshot (root MFA status, root access-key
status, account-level IAM billing access setting, IAM billing principals,
Cost Anomaly Detection monitors/subscriptions, budgets, free-tier alert
preference) and applies the ordered classification logic:

1. Root account security — access keys present (CRITICAL), MFA disabled
   (CRITICAL). Root has unlimited billing power.
2. Billing access model — master switch DEACTIVATED (root-only, HIGH) vs
   ACTIVATED with IAM delegation.
3. Cost Anomaly Detection — no monitors means cost spikes undetected.
4. Billing budgets — no budgets means no spend guardrails.
5. Free-tier usage alerts — disabled means surprise charges possible.
6. Aggregation — worst finding wins (ROOT_BILLING >
   NO_ANOMALY_DETECTION > CONFIG_GAP > OK).

Emits a deterministic VERDICT per account:

```text
ACCOUNT: <account-id>
VERDICT: ROOT_BILLING | NO_ANOMALY_DETECTION | CONFIG_GAP | OK
RISK: CRITICAL | HIGH | MEDIUM | LOW
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [MEDIUM] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Provide a billing configuration snapshot and ask any of:

- "audit my billing configuration"
- "is root MFA enabled on this account?"
- "does my admin user have billing access?"
- "is Cost Anomaly Detection set up?"
- "do I have billing budgets?"
- "are free-tier usage alerts enabled?"

A bare account ID + any audit verb ("audit billing on this account",
"check billing posture") also routes here via the orchestrator.

## Inputs

- Root security: `AccountMFAEnabled` and `AccountAccessKeysPresent` from
  `aws iam get-account-summary`.
- Account-level "IAM User and Role Access to Billing Information" setting
  (ACTIVATED or DEACTIVATED — from the Billing console, not IAM).
- IAM billing principals: any user/group/role with billing actions
  (`aws-portal:*`, `ce:*`, `cur:*`, `budgets:*`, `savingsplans:*`,
  `pricing:*`, `tax:*`, `invoicing:*`, `payments:*`).
- Cost Anomaly Detection monitors and subscriptions.
- Billing budgets and their notifications.
- Free-tier usage alert preference (Billing console preference).

## Outputs

- One VERDICT block per account (multiple findings aggregate to the worst
  verdict).
- Enumerated FINDINGS list with per-finding risk level and step citation.
- Specific remediation: delete root keys, enable root MFA, activate IAM
  billing access, create CAD monitors/subscriptions, create budgets,
  enable free-tier alerts.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for FinOps billing governance).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of billing-
  related policies attached to FinOps roles and groups.
