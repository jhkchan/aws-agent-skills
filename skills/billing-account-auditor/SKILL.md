---
name: billing-account-auditor
description: Audits AWS account billing posture across five dimensions — root account security (MFA + access keys), IAM user/group billing access delegation vs root-only, AWS Cost Anomaly Detection enablement, billing budgets/alerts coverage, and free-tier usage alerts. Emits a deterministic verdict (ROOT_BILLING | NO_ANOMALY_DETECTION | CONFIG_GAP | OK) per account with enumerated findings and specific CLI remediation. Use when reviewing billing access, checking cost anomaly detection, auditing budget coverage, validating root MFA, or hardening billing posture for FinOps compliance.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline configuration classification. Live-account audits use aws iam get-account-summary, aws ce list-cost-anomaly-monitors, aws budgets describe-budgets, and aws ce get-anomaly-subscriptions (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  verdict_shape: ROOT_BILLING | NO_ANOMALY_DETECTION | CONFIG_GAP | OK
  when_to_use: Reviewing billing access delegation, checking if Cost Anomaly Detection is enabled, auditing budget/alert coverage, validating root MFA, or hardening billing posture before a FinOps compliance review.
  activation_triggers: audit my billing configuration, check billing access, is Cost Anomaly Detection enabled, do I have billing budgets, is root MFA enabled, billing alerts configured, free tier usage alerts, who can access billing, root account billing access, billing posture audit
  invocation_schema: 'Input: either (a) an account billing configuration snapshot (root MFA status, IAM billing access setting, IAM billing policies, CAD monitors, budgets, free-tier alert preference), OR (b) an account-id for live-account audit. Output: deterministic ACCOUNT/VERDICT/RISK/REASON/ FINDINGS/REMEDIATION block, where VERDICT is ROOT_BILLING, NO_ANOMALY_DETECTION, CONFIG_GAP, or OK.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Billing, billing access, root MFA, Cost Anomaly Detection, billing budgets, free-tier alerts, aws-portal, Cost Explorer, FinOps, billing audit, cost governance, IAM billing delegation, account security, budget alerts, billing preferences
  tags: billing, finops, cost-management, security, root-mfa, anomaly-detection, audit
---

# Billing Account Auditor

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across five
dimensions, and two are in a class of their own — root access keys (bypass
MFA for unlimited billing API access) and the IAM-billing-access master
switch (overrides every IAM policy if deactivated).

Billing is the financial root of trust for an AWS account. The root user has
unlimited billing power by definition — view, modify, close the account.
Unlike KMS or S3 where the damage radius is one key or bucket, a billing
compromise can:
- **Close the entire account** (`aws-portal:ModifyAccount` — terminates all
  resources across every region and service).
- **Delete payment methods** and trigger service suspension.
- **Modify tax invoices**, Cost Explorer settings, and Savings Plans.

Three principles drive the classification:
- **Billing access must be delegated to IAM principals** — not concentrated
  on root. Root should never be used for day-to-day billing operations.
- **Root must be locked down** — MFA enabled, zero access keys. A root
  access key is a permanent, MFA-bypassing billing backdoor.
- **Automated cost controls must be active** — Cost Anomaly Detection for
  ML-based spike detection, budgets for threshold guardrails. Without them,
  a single misconfiguration (e.g., an over-provisioned RDS instance or a
  compromised credential spinning EC2) can accumulate thousands of dollars
  before anyone notices.

## Quick reference — severity thresholds

| Condition | Verdict | Risk | Step |
|---|---|---|---|
| Root access keys present (`AccountAccessKeysPresent: 1`) | **ROOT_BILLING** | CRITICAL | Step 1 |
| Root MFA not enabled (`AccountMFAEnabled: 0`) | **ROOT_BILLING** | CRITICAL | Step 1 |
| IAM billing access DEACTIVATED (master switch off) | **ROOT_BILLING** | HIGH | Step 2 |
| IAM billing access ACTIVATED but no IAM principal has billing actions | **ROOT_BILLING** | MEDIUM | Step 2 |
| No Cost Anomaly Detection monitors | **NO_ANOMALY_DETECTION** | MEDIUM | Step 3 |
| CAD monitors exist but no alert subscriptions | **NO_ANOMALY_DETECTION** | LOW | Step 3 |
| No billing budgets configured | **CONFIG_GAP** | LOW | Step 4 |
| Budgets exist but no alert notifications | **CONFIG_GAP** | LOW | Step 4 |
| Free-tier usage alerts not enabled | **CONFIG_GAP** | LOW | Step 5 |
| All dimensions properly configured | **OK** | LOW | Step 6 |

The verdict is the **maximum-severity** finding: ROOT_BILLING >
NO_ANOMALY_DETECTION > CONFIG_GAP > OK.

## Pre-flight: account context gate (run before classification)

Several account attributes change the audit scope. Misclassifying them
produces false positives.

| Attribute | Value | Effect on audit |
|---|---|---|
| Account type | **Organization member** (linked account) | Billing is managed by the **payer (management) account**. The member account's own billing-access setting and IAM billing policies are secondary — the payer controls consolidated billing. Still audit root MFA and CAD for the member account. Skip billing-access model and budgets if the payer handles them. Note this in the output. |
| Account type | **Payer (management) account** | Full audit applies. This is the account that receives the invoice. |
| Account type | **Standalone** | Full audit applies. |
| Cost Explorer | Not yet enabled | `ce:*` actions fail until an account admin enables Cost Explorer in the console (one-way operation). If CE is not enabled, CAD cannot be configured either — both are CONFIG_GAP at minimum. Flag the CE-not-enabled state explicitly. |
| Region | GovCloud (us-gov-*) | Billing APIs behave identically, but some console features differ. No change to classification. |

**If the input is incomplete** (missing root MFA status, missing billing
access setting), output:

```text
ACCOUNT: <account-id>
VERDICT: ERROR
REASON: Billing configuration snapshot is incomplete — <missing field>.
Cannot classify safely.
REMEDIATION: Collect the missing data and re-audit. See the data-collection
commands in Pre-flight.
```

**Live-account data collection commands:**

```bash
# Root MFA + access-key status
aws iam get-account-summary --profile <p> --query 'SummaryMap.[AccountMFAEnabled,AccountAccessKeysPresent]'

# IAM billing access (account-level master switch — NOT in IAM)
aws account get-contact-information --profile <p>  # billing contact email
# The IAM-billing-access setting is console-only:
# Billing console → Account → IAM User and Role Access to Billing Information

# Cost Anomaly Detection monitors
aws ce list-cost-anomaly-monitors --profile <p> --region us-east-1

# Cost Anomaly Detection subscriptions (alerts)
aws ce get-anomaly-subscriptions --profile <p> --region us-east-1 \
  --monitor-arn <monitor-arn>

# Budgets
aws budgets describe-budgets --account-id <acct> --profile <p>

# Free-tier usage alerts (console preference, no direct CLI):
# Billing console → Billing preferences → Receive Free Tier Usage Alerts
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious AWS Billing behaviors

These behaviors are easy to misjudge without operational FinOps experience.
Each changes a verdict if ignored:

- **AdministratorAccess does NOT grant billing access.** Billing actions
  (`aws-portal:*`, `ce:*`, `cur:*`, `budgets:*`, `savingsplans:*`,
  `pricing:*`, `tax:*`, `invoicing:*`, `payments:*`) are in a separate
  namespace. An IAM admin user with `Action: "*"` on `Resource: "*"`
  STILL cannot access the billing console or call billing APIs unless
  the account-level master switch is ACTIVATED. This is the #1 source of
  "why can't my admin see billing?" support tickets.

- **The account-level "IAM User and Role Access to Billing Information"
  setting is a MASTER SWITCH.** If DEACTIVATED, it OVERRIDES all IAM
  policies — even a user with explicit `aws-portal:ViewBilling` in an
  inline policy CANNOT access billing. This setting lives in the Billing
  console (Account → IAM User and Role Access), NOT in IAM. There is no
  CLI command to read it; it must be checked in the console or via
  `aws account` API calls. An account with this DEACTIVATED is effectively
  root-only for billing regardless of IAM configuration.

- **Root access keys bypass MFA entirely.** A root access key
  (`AccountAccessKeysPresent: 1`) gives programmatic API access to every
  billing API (`aws-portal:*`, `ce:*`, `budgets:*`, `cur:*`) with NO
  second factor. MFA protects console sign-in only; API calls authenticate
  with the access key alone. This is why root access keys are a CRITICAL
  billing finding — they are an MFA-bypassing billing backdoor. AWS best
  practice: root access keys should NEVER exist. If one does, it must be
  deleted immediately.

- **`aws-portal:*` actions are CONSOLE-ONLY.** They control which billing
  console pages a principal can view/modify. You cannot call
  `aws-portal:ViewBilling` via the CLI or SDK — it is not a standard API
  action. Programmatic billing access uses `ce:*`, `cur:*`, `budgets:*`.
  When auditing IAM billing policies, `aws-portal:ViewBilling` grants
  console access; `ce:GetCostAndUsage` grants programmatic Cost Explorer
  access. Both are needed for full billing visibility.

- **Cost Explorer must be explicitly ENABLED.** `ce:*` calls return an
  error until an account admin enables CE via the console (Billing → Cost
  Explorer → Launch). This is a ONE-WAY operation — once enabled, it
  cannot be disabled. CE takes ~24 hours to populate initial cost data.
  If CE is not enabled, Cost Anomaly Detection is also unavailable (CAD
  is a CE sub-service). Both are CONFIG_GAP findings.

- **Cost Anomaly Detection (CAD) is NOT Budgets.** CAD uses ML to detect
  anomalous spending patterns (unexpected spikes, unusual service
  adoption). Budgets are static threshold alerts ("notify me if spend
  exceeds $X"). They serve different purposes: CAD catches the
  unexpected; budgets enforce the expected. A well-governed account has
  BOTH. CAD has two components: **monitors** (define what to watch) and
  **subscriptions** (define who to notify and the threshold). A monitor
  without a subscription detects anomalies but nobody gets alerted.

- **Budgets have a 100-per-account quota** (soft limit, raisable via
  Support). A large organization with many member accounts can hit this
  fast if each account creates per-service budgets. Prefer fewer, broader
  budgets (one total-cost budget + one per business unit) over many
  narrow ones.

- **Free-tier usage alerts email the billing contact**, not the root
  email. If the billing alternate contact is not set, alerts default to
  the root email only. This is a separate preference from budgets — it
  specifically warns when free-tier limits are approaching, preventing
  surprise charges for accounts that should be free-tier-only.

- **Root MFA status is NOT available via `iam list-mfa-devices`.** That
  API lists IAM-user MFA devices only. The root MFA status is available
  via `aws iam get-account-summary` → `AccountMFAEnabled` (1 = enabled,
  0 = disabled), or via the credential report (`aws iam
  get-credential-report` → root user row → `mfa_active` column). Using
  the wrong API silently produces a false "no root MFA" finding because
  root does not appear in `list-mfa-devices`.

- **Consolidated billing changes the audit for member accounts.** In an
  AWS Organization, the payer account receives the invoice and manages
  payment methods. Member accounts CAN still have their own budgets,
  Cost Explorer data, and CAD monitors — these are per-account. But the
  billing-access model and payment-method management are payer-only.
  When auditing a member account, skip Step 2 (billing access model)
  unless the member has its own billing requirements (e.g., chargeback).

- **`aws ce list-cost-anomaly-monitors` is region-pinned to us-east-1.**
  Cost Explorer and CAD APIs are global services but the API endpoint is
  in us-east-1. Calling from another region works but may incur
  cross-region latency. Always use `--region us-east-1` for CE/CAD CLI
  commands to avoid unexpected regional routing.

- **Budget notification thresholds are cumulative, not instantaneous.**
  A budget alert at 80% fires when total spend for the period reaches
  80% of the budget — it does NOT fire if a single day's spend is 80% of
  the daily equivalent. This means a sudden spike on day 1 of the month
  won't trigger a budget alert until cumulative spend crosses the
  threshold. CAD fills this gap (it detects daily anomalies), which is
  why both are needed.

### Step 1: Root account security (highest priority — unlimited billing power)

Root has irrevocable billing authority. An unprotected root is the
highest-severity billing risk because it can close the account, delete
payment methods, and disable all cost controls in seconds.

Check `AccountAccessKeysPresent` and `AccountMFAEnabled` from
`aws iam get-account-summary`:

- **Root access keys present** (`AccountAccessKeysPresent: 1`) →
  **ROOT_BILLING (CRITICAL)**. This is the single most dangerous billing
  configuration. The key bypasses MFA for every billing API call. Delete
  it immediately — there is no legitimate use case for root access keys.
  Anyone with the key can close the account programmatically.

- **Root MFA not enabled** (`AccountMFAEnabled: 0`) → **ROOT_BILLING
  (CRITICAL)**. The root account has unlimited billing power and is
  protected by only a password. If the password is compromised (phishing,
  credential stuffing), the attacker has full billing control. Enable
  a hardware or virtual MFA on root immediately.

Both findings can be present simultaneously. Each independently drives
the verdict to ROOT_BILLING with CRITICAL risk.

**If root access keys are present AND root MFA is disabled**, the account
is in its most vulnerable billing posture — the access key bypasses the
absent MFA entirely, making the MFA gap irrelevant for programmatic
attacks. Treat as CRITICAL and remediate both findings.

### Step 2: Billing access model — IAM delegation vs root-only

Check whether billing operations require root or are delegated to IAM
principles. This step has two sub-checks:

**Sub-check 2a: Account-level master switch.** The "IAM User and Role
Access to Billing Information" setting (Billing console → Account) controls
whether ANY IAM principal can access billing. This is NOT an IAM policy —
it is a master switch that OVERRIDES all IAM policies.

- **DEACTIVATED** → **ROOT_BILLING (HIGH)**. Only root can access billing
  console and APIs. Every billing operation — viewing invoices, creating
  budgets, checking Cost Explorer — requires root login. This forces root
  usage for routine FinOps work, violating least-privilege and increasing
  root-credential exposure. Activate this setting to enable IAM delegation.

- **ACTIVATED** → Proceed to sub-check 2b.

**Sub-check 2b: IAM billing principals exist.** Even with the master
switch ON, an account is effectively root-only if no IAM user, group, or
role has any billing actions in their policies. The master switch enables
the CAPABILITY; IAM policies grant the actual ACCESS.

- **No IAM principal has any billing actions** (`aws-portal:*`, `ce:*`,
  `cur:*`, `budgets:*`, `savingsplans:*`, `pricing:*`, `tax:*`,
  `invoicing:*`, `payments:*`) → **ROOT_BILLING (MEDIUM)**. The capability
  is on but nobody was granted access. Billing operations still require
  root. Create an IAM group with `aws-portal:ViewBilling` + `ce:*` +
  `budgets:*` and assign FinOps team members.

- **One or more IAM principals have billing actions** → Check least-
  privilege scope. `aws-portal:*` on `Resource: "*"` is acceptable for a
  billing-admin role but should be scoped to a named group, not individual
  users. Flag wildcard `aws-portal:ModifyBilling` on non-admin principals
  as a MEDIUM finding (does not change verdict). Proceed to Step 3.

### Step 3: Cost Anomaly Detection (automated cost-spike detection)

Check for Cost Anomaly Detection monitors via
`aws ce list-cost-anomaly-monitors --region us-east-1`:

- **Zero monitors** → **NO_ANOMALY_DETECTION (MEDIUM)**. No ML-based cost
  spike detection. A misconfigured service, compromised credential, or
  unexpected data-transfer surge accumulates charges undetected. CAD is
  free (included with Cost Explorer) — there is no cost reason to skip it.

- **Monitors exist but zero alert subscriptions** →
  **NO_ANOMALY_DETECTION (LOW)**. CAD detects anomalies but nobody
  receives notifications. The anomalies are visible in the console but
  no email/SNS is sent. Add an anomaly subscription to close the gap.

- **Monitors + subscriptions exist** → OK for this dimension. Verify the
  subscription threshold is reasonable (default is $100; adjust to the
  account's spend profile). A $10,000/month account with a $100 threshold
  generates noise; a $500/month account with a $100 threshold is appropriate.

**If Cost Explorer is not enabled**, CAD is also unavailable. This is
**NO_ANOMALY_DETECTION (MEDIUM)** — note the root cause (CE not enabled)
in the finding text.

### Step 4: Billing budgets and alerts (threshold guardrails)

Check budgets via `aws budgets describe-budgets --account-id <acct>`:

- **Zero budgets** → **CONFIG_GAP (LOW)**. No spend guardrails. Without a
  budget, there is no automated notification when spend exceeds a planned
  amount. At minimum, create one total-cost budget at the account's monthly
  spend with alerts at 50%, 80%, and 100%.

- **Budgets exist but no notifications** → **CONFIG_GAP (LOW)**. Budgets
  without alert notifications are passive — they track spend but do not
  alert. Verify each budget has at least one notification.

- **Budgets + notifications exist** → OK for this dimension.

### Step 5: Free-tier usage alerts (surprise-charge prevention)

Check the "Receive Free Tier Usage Alerts" preference (Billing console →
Billing preferences):

- **Free-tier alerts not enabled** → **CONFIG_GAP (LOW)**. Free-tier-
  eligible services can exceed limits silently, generating charges on an
  account expected to stay within free tier. Enable this preference to
  receive email alerts when free-tier usage approaches 85%.

- **Free-tier alerts enabled** → OK for this dimension.

**Alternate billing contact:** verify a billing alternate contact email is
set (`aws account get-contact-information`). If not set, free-tier alerts
default to root email only. This does not change the verdict but should be
noted as an operational recommendation.

### Step 6: Aggregation — worst finding wins

```text
verdict = max(root_security, billing_access, anomaly_detection, budgets, free_tier)
```

Where ROOT_BILLING > NO_ANOMALY_DETECTION > CONFIG_GAP > OK. If no findings
(all dimensions OK), the verdict is **OK**.

## Output format (per account)

```text
ACCOUNT: <account-id or alias>
VERDICT: ROOT_BILLING | NO_ANOMALY_DETECTION | CONFIG_GAP | OK
RISK: CRITICAL | HIGH | MEDIUM | LOW
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [MEDIUM] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — root access keys + no CAD

```text
ACCOUNT: 111111111111
VERDICT: ROOT_BILLING
RISK: CRITICAL
REASON: Root account has active access keys (AccountAccessKeysPresent: 1) —
a permanent MFA-bypassing billing backdoor (Step 1). Cost Anomaly Detection
is also not enabled, compounding the exposure.
FINDINGS:
  - [CRITICAL] Root access keys present — API access to all billing actions
    without MFA (Step 1)
  - [MEDIUM] No Cost Anomaly Detection monitors — cost spikes undetected
    (Step 3)
  - [LOW] No billing budgets configured (Step 4)
  - [OK] Root MFA is enabled (Step 1)
  - [OK] IAM billing access is ACTIVATED with delegated principals (Step 2)
REMEDIATION:
  1. CRITICAL — Delete root access keys immediately:
     aws iam delete-access-key --access-key-id <AKIA...> (run as root in
     console; this is the only way to manage root keys).
  2. MEDIUM — Create a Cost Anomaly Detection monitor:
     aws ce create-anomaly-monitor --monitor-name "AllServices" \
       --monitor-type DIMENSIONAL --region us-east-1
     Then create a subscription:
     aws ce create-anomaly-subscription --subscription-name "FinOpsAlert" \
       --monitor-arn <arn> --threshold 100.0 \
       --frequency IMMEDIATE --region us-east-1.
  3. Create a total-cost budget with 80% and 100% alerts.
```

## Anti-Patterns — NEVER

- NEVER assume `AdministratorAccess` grants billing access. Billing actions
  (`aws-portal:*`, `ce:*`, `cur:*`, `budgets:*`) are in a separate
  namespace that must be explicitly granted. An admin user who cannot see
  the billing console is NOT a misconfiguration — it is the default
  behavior when the master switch is off or billing policies are absent.

- NEVER classify an account with root access keys as anything other than
  ROOT_BILLING. Root access keys bypass MFA for every billing API call
  — they are a permanent, MFA-bypassing billing backdoor. Even if every
  other dimension is perfectly configured, a root access key is CRITICAL.

- NEVER treat `AccountMFAEnabled: 0` as a minor finding. The root account
  has unlimited billing power including account closure. Without MFA,
  a compromised root password gives an attacker full financial control.
  This is always CRITICAL and always ROOT_BILLING.

- NEVER use `aws iam list-mfa-devices` to check root MFA. That API lists
  IAM-user MFA devices only — the root user does not appear in the
  results. Use `aws iam get-account-summary` → `AccountMFAEnabled`, or
  parse the credential report's root-user `mfa_active` column. Using the
  wrong API silently produces a false negative.

- NEVER assume the IAM billing-access master switch is an IAM policy. It
  is an account-level setting (Billing console → Account) that OVERRIDES
  all IAM policies. If DEACTIVATED, even a user with explicit
  `aws-portal:ViewBilling` cannot access billing. Checking IAM policies
  alone misses this gate.

- NEVER recommend disabling the IAM billing-access master switch as a
  security hardening step. While it concentrates billing access on root,
  it also prevents legitimate IAM-based FinOps workflows (budgets, Cost
  Explorer dashboards, automated cost alerts via Lambda). The correct
  hardening is to ACTIVATE the switch and delegate billing access via
  least-privilege IAM group policies.

- NEVER confuse Cost Anomaly Detection with Budgets. CAD uses ML to
  detect unexpected spending anomalies (dynamic baselines). Budgets are
  static threshold alerts. Both serve different purposes and both should
  be configured. Recommending budgets as a replacement for CAD misses
  the class of problems CAD catches (novel spend patterns, sudden
  data-transfer surges, compromised credentials spinning resources).

- NEVER recommend creating per-service budgets for every AWS service.
  Budgets have a 100-per-account quota (soft limit). A large account
  with 50+ services hits this fast. Prefer one total-cost budget plus
  per-business-unit or per-member-account budgets.

- NEVER assume a budget without notifications provides alerting. Budgets
  are passive trackers unless notification rules are attached. Always
  verify `aws budgets describe-notifications-for-budget` returns at least
  one entry per budget.

- NEVER skip the consolidated-billing context for Organization member
  accounts. A member account's billing is managed by the payer — the
  member's own billing-access setting may be irrelevant. Still audit
  root MFA, CAD, and local budgets for the member account, but note
  that payment methods and invoicing are payer-controlled.

- NEVER treat `aws-portal:ModifyBilling` on an IAM principal as a
  security finding by itself. Billing-admin roles legitimately need
  modify access to manage budgets, Savings Plans, and tax settings.
  Flag it only if attached to a principal that should be read-only
  (e.g., a developer role). The finding is about the PRINCIPAL, not
  the action.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing billing
  operation (deleting root access keys, activating/deactivating the
  billing-access master switch, creating/deleting budgets, modifying
  CAD monitors), the auditor MUST emit:
  `CONFIRM: About to <action> on account <acct>. This affects
  <consequence>. Proceed? (yes/no)`
- **Root access key deletion is irreversible and root-only.** Root keys
  can only be managed by signing in as root in the console — IAM users
  (even admins) cannot delete root keys via CLI. The auditor cannot
  automate this; it must surface as a human-action remediation step.
- **The billing-access master switch change is instantaneous.** Activating
  or deactivating it takes effect immediately across all IAM principals.
  Deactivating it revokes billing access for all IAM users — verify no
  automated billing workflows (Lambda, Cost Explorer dashboards) depend
  on IAM billing access before toggling.
- **Budget creation does not modify spend.** Creating a budget is a
  read-only observability action — it tracks spend without enforcing
  limits. Budgets do NOT cap or block spending. Be explicit about this
  in the remediation; a common misconception is that a budget prevents
  overage.
- **CAD monitor creation is free.** Cost Anomaly Detection is included
  with Cost Explorer at no additional cost. There is no cost concern
  with creating monitors and subscriptions.
- **Verify Cost Explorer is enabled before creating CAD monitors.** CAD
  is a CE sub-service. If CE is not enabled, `create-anomaly-monitor`
  fails. Enable CE in the console first (one-way operation).

## Remediation guidance

### For ROOT_BILLING — root access keys present (Step 1, CRITICAL)

1. **Immediately** sign in to the console as root and delete the access
   key. This is the ONLY way to manage root keys — IAM admins cannot.
2. Audit CloudTrail for API calls from the root access key during the
   exposure window. Any billing API call (`aws-portal:*`, `budgets:*`,
   `ce:*`) from the key may indicate unauthorized access.
3. If the key was used to modify billing (changed payment methods,
   enabled/disabled budgets), review the change and revert if malicious.
4. Enable root MFA if not already enabled.

### For ROOT_BILLING — root MFA not enabled (Step 1, CRITICAL)

1. Sign in as root and enable a virtual or hardware MFA device.
2. Verify by checking `aws iam get-account-summary` shows
   `AccountMFAEnabled: 1`.
3. Ensure the root password is strong and not shared.

### For ROOT_BILLING — IAM billing access DEACTIVATED (Step 2, HIGH)

1. Activate "IAM User and Role Access to Billing Information" in the
   Billing console (Account → scroll to IAM User and Role Access →
   Edit → Activate). This takes effect immediately.
2. Create an IAM group `BillingViewers` with a managed policy granting
   `aws-portal:ViewBilling`, `aws-portal:ViewUsage`, `ce:GetCostAndUsage`,
   `ce:GetDimensions`, `ce:GetTags`, `budgets:ViewBudget`.
3. Create an IAM group `BillingAdmins` adding `aws-portal:ModifyBilling`,
   `budgets:ModifyBudget`, `savingsplans:*` to the viewers policy.
4. Assign FinOps team members to the appropriate group.

### For NO_ANOMALY_DETECTION — CAD not enabled (Step 3, MEDIUM)

1. Ensure Cost Explorer is enabled (Billing → Cost Explorer → Launch).
   This is a one-way operation; it cannot be disabled once enabled.
2. Create the default monitor:
   ```bash
   aws ce create-anomaly-monitor --monitor-name "AllServicesMonitor" \
     --monitor-type DIMENSIONAL \
     --monitor-specification '{"Dimension":"SERVICE","MatchOptions":["EQUALS"],"Values":[]}' \
     --profile <p> --region us-east-1
   ```
   An empty `Values` array means "monitor all services."
3. Create an alert subscription:
   ```bash
   aws ce create-anomaly-subscription \
     --subscription-name "FinOpsAnomalyAlert" \
     --account-id <acct> \
     --monitor-arn <monitor-arn> \
     --threshold 100.0 \
     --frequency IMMEDIATE \
     --subscription-status ACTIVE \
     --notification-email-list finops@example.com \
     --profile <p> --region us-east-1
   ```
   Adjust `$100` threshold to the account's spend profile.

### For CONFIG_GAP — no budgets (Step 4, LOW)

1. Create a total-cost budget:
   ```bash
   aws budgets create-budget --account-id <acct> \
     --budget '{
       "BudgetName":"MonthlyCostBudget",
       "BudgetLimit":{"Amount":"5000","Unit":"USD"},
       "TimeUnit":"MONTHLY",
       "BudgetType":"COST"
     }' \
     --notifications-with-subscribers '[
       {"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"},
        "Subscribers":[{"SubscriptionType":"EMAIL","Address":"finops@example.com"}]}
     ]' \
     --profile <p>
   ```
2. Adjust the budget limit to match the account's monthly spend.

### For CONFIG_GAP — free-tier alerts not enabled (Step 5, LOW)

1. Enable in the Billing console: Billing preferences → Receive Free Tier
   Usage Alerts → Edit → check the box → Save.
2. Verify a billing alternate contact email is set so alerts reach the
   right team:
   ```bash
   aws account put-alternate-contact --alternate-contact-type BILLING \
     --email-address "finops@example.com" --name "FinOps Team" \
     --phone-number "+1-555-0100" --title "Billing" \
     --profile <p>
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic review of budget thresholds as spend patterns change.
3. Recommend reviewing CAD anomaly reports weekly to tune thresholds.

## Recent AWS features (2024-2026)

- **AWS Billing Conductor updates (2024):** Billing Conductor now supports proportional splitting with CUR 2.0. Auditors should check whether Billing Conductor is enabled and whether the billing group pipeline is healthy — misconfigured billing conductors produce incorrect chargebacks.
- **FOCUS-aligned billing (2025):** AWS introduced FOCUS-compatible cost data exports. Auditors should verify that cost reporting aligns with the FOCUS spec if the organization uses cross-cloud FinOps tooling.
- **Cost Anomaly Detection improvements:** CAD now supports more granular dimensions and improved ML models. No new audit-surface fields, but auditors should re-evaluate anomaly detection thresholds after upgrades.

## Domain

AWS CloudOps / FinOps Billing Governance & Account Security.

## AWS documentation

- **Service documentation** — [AWS Billing User Guide](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-what-is.html)
- **Security** — [Security in AWS Billing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/security.html)
- **API reference** — [AWS Cost Management API Reference](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/) (covers Cost Explorer, Budgets, and Cost Anomaly Detection APIs)
- **CLI reference** — [AWS Cost Explorer (`ce`) CLI](https://docs.aws.amazon.com/cli/latest/reference/ce/) · [AWS Budgets (`budgets`) CLI](https://docs.aws.amazon.com/cli/latest/reference/budgets/)
- **AWS Billing Conductor** — [Billing Conductor User Guide](https://docs.aws.amazon.com/billingconductor/latest/userguide/what-is-billingconductor.html)
- **FOCUS-aligned billing** — [Announcing FOCUS-aligned cost and usage data](https://aws.amazon.com/blogs/aws-cloud-financial-management/announcing-focus-aligned-cost-and-usage-data/)
