# Advanced Patterns (load on demand) — Billing Account Auditor

Expert-knowledge deep dives and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious AWS Billing behaviors (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **AWS Billing Conductor updates (2024):** Billing Conductor now supports proportional splitting with CUR 2.0. Auditors should check whether Billing Conductor is enabled and whether the billing group pipeline is healthy — misconfigured billing conductors produce incorrect chargebacks.
- **FOCUS-aligned billing (2025):** AWS introduced FOCUS-compatible cost data exports. Auditors should verify that cost reporting aligns with the FOCUS spec if the organization uses cross-cloud FinOps tooling.
- **Cost Anomaly Detection improvements:** CAD now supports more granular dimensions and improved ML models. No new audit-surface fields, but auditors should re-evaluate anomaly detection thresholds after upgrades.
