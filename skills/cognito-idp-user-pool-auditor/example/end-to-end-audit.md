# End-to-End Example: Cognito User Pool Audit

A walkthrough showing how to use the `cognito-idp-user-pool-auditor` skill
from invocation through remediation. Mirrors the structured-eval pattern of shipping a
concrete worked example per skill.

---

## Scenario

You are hardening a Cognito user pool for a SaaS application before
production launch. The pool has two app clients: a user-facing web client
and a backend service client. You need to audit both for identity-security
risks.

1. **`saas-prod-pool`** — main user pool.
   - MfaConfiguration: OPTIONAL, EnabledMfas: [SMS, SOFTWARE_TOKEN_MFA]
   - Password policy: 8 chars, 3 of 4 complexity rules
   - AdvancedSecurityMode: OFF
2. **`web-client`** — SPA front-end.
   - GenerateSecret: false, ExplicitAuthFlows: [ALLOW_USER_PASSWORD_AUTH]
   - PreventUserExistenceErrors: LEGACY
   - AllowedOAuthFlows: [implicit]
   - CallbackURLs: [https://app.saas.example.com/callback]
3. **`backend-client`** — server-side admin tool.
   - GenerateSecret: true
   - ExplicitAuthFlows: [ALLOW_ADMIN_USER_PASSWORD_AUTH,
     ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH]
   - PreventUserExistenceErrors: ENABLED

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:audit-cognito-user-pool
```

Then paste the pool and client configurations.

### Option B: Natural language

```
You: "Audit this Cognito user pool before production launch:

  User Pool: saas-prod-pool
  MfaConfiguration: OPTIONAL
  EnabledMfas: [SMS, SOFTWARE_TOKEN_MFA]
  PasswordPolicy:
    MinimumLength: 8
    RequireUppercase: true
    RequireLowercase: true
    RequireNumbers: true
    RequireSymbols: false
  UserPoolAddOns:
    AdvancedSecurityMode: OFF

  App Client: web-client
  GenerateSecret: false
  ExplicitAuthFlows: [ALLOW_USER_PASSWORD_AUTH]
  PreventUserExistenceErrors: LEGACY
  AllowedOAuthFlows: [implicit]
  CallbackURLs: [https://app.saas.example.com/callback]

  App Client: backend-client
  GenerateSecret: true
  ExplicitAuthFlows: [ALLOW_ADMIN_USER_PASSWORD_AUTH, ALLOW_USER_SRP_AUTH]
  PreventUserExistenceErrors: ENABLED
"
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "audit my Cognito user pool for security"
```

Output:

```
[Phase: Audit | Skills routed: cognito-idp-user-pool-auditor]

Primary route: cognito-idp-user-pool-auditor (score: 22)
```

---

## Step 2 — Skill produces deterministic verdicts

The skill applies its classification logic in precedence order (INSECURE
conditions first, worst-match-wins) and emits a per-pool report:

```text
USER POOL: saas-prod-pool
VERDICT: INSECURE
REASON: Multiple critical deficiencies: web-client has AllowedOAuthFlows
        [implicit] (Rule 1b — OAuth implicit flow, token leakage via URL
        fragment) AND PreventUserExistenceErrors LEGACY (Rule 1c — user
        enumeration). Additionally, web-client uses ALLOW_USER_PASSWORD_AUTH
        without SRP on a public client (GenerateSecret: false). Pool-level
        MFA is OPTIONAL (not enforced) and AdvancedSecurityMode is OFF.
        The backend-client's admin auth flow (Rule 2g) is WEAK but does
        not change the pool verdict since INSECURE is worse.
RISK: CRITICAL
REMEDIATION: Priority order — (1) Switch web-client AllowedOAuthFlows from
             [implicit] to [code] to eliminate token leakage. (2) Set
             PreventUserExistenceErrors to ENABLED on web-client.
             (3) Transition MfaConfiguration from OPTIONAL to ON after
             user enrollment campaign. (4) Replace ALLOW_USER_PASSWORD_AUTH
             with ALLOW_USER_SRP_AUTH + ALLOW_REFRESH_TOKEN_AUTH on
             web-client (confirm SDK supports SRP). (5) Enable
             AdvancedSecurityMode ENFORCED. (6) Evaluate whether
             backend-client needs admin auth flow or can use SRP only.
```

---

## Step 3 — Pipeline integration (Prioritize + Remediate)

When invoked through the orchestrator (`/aws:pipeline`), the findings flow
into the Prioritize and Remediate phases:

```
[Phase: Prioritize | Findings: 1 CRITICAL (3 sub-issues) | Skills routed: orchestrator]

1. CRITICAL: web-client OAuth implicit flow — tokens leaked via URL fragment
   (XSS, browser history, Referer header exposure)
2. CRITICAL: web-client PreventUserExistenceErrors LEGACY — user enumeration
   enables targeted credential stuffing
3. CRITICAL: web-client ALLOW_USER_PASSWORD_AUTH on public client — password
   sent to API without SRP protection
4. HIGH: pool-level MFA OPTIONAL — users can skip MFA enrollment
5. HIGH: pool-level AdvancedSecurityMode OFF — no adaptive threat protection
6. HIGH: backend-client admin auth flow — bypasses SRP (acceptable for
   trusted backend, flag for review)

[Phase: Remediate | Skills routed: cognito-idp-user-pool-auditor]
```

### Remediation commands

**Capture current state for rollback:**

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id us-east-1_xxxxx \
  --output json > /tmp/saas-prod-pool-backup-$(date +%s).json

aws cognito-idp describe-user-pool-client \
  --user-pool-id us-east-1_xxxxx \
  --client-id <web-client-id> \
  --output json > /tmp/web-client-backup-$(date +%s).json
```

**Fix web-client (additive + flow change):**

```bash
# 1. Switch OAuth from implicit to code flow (eliminates token leakage)
aws cognito-idp update-user-pool-client \
  --user-pool-id us-east-1_xxxxx \
  --client-id <web-client-id> \
  --allowed-o-auth-flows code \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --prevent-user-existence-errors ENABLED
```

**Fix pool-level controls:**

```bash
# 2. Enable Advanced Security Features (ENFORCED mode)
aws cognito-idp update-user-pool \
  --user-pool-id us-east-1_xxxxx \
  --user-pool-add-ons AdvancedSecurityMode=ENFORCED

# 3. Strengthen password policy
aws cognito-idp update-user-pool \
  --user-pool-id us-east-1_xxxxx \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 12,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": true,
      "TemporaryPasswordValidityDays": 7
    }
  }'

# 4. Transition MFA: set to OPTIONAL first, then ON after enrollment
#    Do NOT set to ON immediately — users without enrolled MFA will be locked out
aws cognito-idp update-user-pool \
  --user-pool-id us-east-1_xxxxx \
  --mfa-configuration OPTIONAL \
  --software-token-mfa-configuration Enabled=true
```

---

## Step 4 — Post-remediation verification

After remediation and MFA enrollment campaign (>90% enrolled), set
`MfaConfiguration: ON` and re-run the audit:

```text
USER POOL: saas-prod-pool
VERDICT: ADEQUATE
REASON: MFA is ON (enforced) with TOTP. Password policy is strong (12 chars,
        all complexity). AdvancedSecurityMode is ENFORCED. web-client uses
        SRP auth with code flow OAuth and PreventUserExistenceErrors ENABLED.
        Backend-client still has ALLOW_ADMIN_USER_PASSWORD_AUTH (Rule 2g) on
        a confidential client — WEAK but acceptable for trusted backend.
        Pool verdict is ADEQUATE due to the backend-client admin auth flow.
RISK: MODERATE
REMEDIATION: If backend-client can migrate to SRP-only, the pool will reach
             OK. Otherwise, scope the admin auth flow to a dedicated
             infrastructure client with restrictive IAM policies.
```

After removing the admin auth flow from backend-client:

```text
USER POOL: saas-prod-pool
VERDICT: OK
REASON: All controls met — MFA ON with TOTP, 12+ char password, ASF ENFORCED,
        SRP-only auth flows, code flow OAuth with HTTPS callbacks,
        PreventUserExistenceErrors ENABLED, token revocation enabled.
RISK: LOW
REMEDIATION: None required. Monitor ASF findings periodically.
```

---

## What the skill catches that a naive review misses

| Config | Naive review | Skill verdict | Why the skill is right |
|---|---|---|---|
| `web-client` OAuth implicit | "OAuth is configured, looks fine" | INSECURE (Rule 1b) | Implicit flow returns tokens in the URL fragment — accessible via browser history, Referer headers, and any script on the callback page. OAuth 2.1 deprecates it. The naive review checks "is OAuth set up?" but not "which grant type?" |
| `web-client` PreventUserExistenceErrors: LEGACY | "Not mentioned, probably fine" | INSECURE (Rule 1c) | LEGACY returns different errors for non-existent vs wrong-password users, enabling username enumeration. Older pools default to LEGACY. |
| `web-client` USER_PASSWORD_AUTH | "Auth flow is configured" | Part of INSECURE (no SRP) | Without SRP, the password is sent to the API. SRP never transmits the password. The naive review doesn't distinguish between auth flows. |
| `backend-client` admin auth flow | "Has a secret, seems OK" | WEAK (Rule 2g) | Even with a secret, admin auth bypasses SRP and requires AWS credentials, expanding the attack surface. Acceptable for trusted backends but should be flagged. |
| Pool-level MFA OPTIONAL | "MFA is available, good" | Would be WEAK (Rule 2a) | Optional MFA means most users skip it. The naive review checks "is MFA configured?" but not "is it enforced?" |

---

## Related artifacts

- **Skill definition:** `skills/cognito-idp-user-pool-auditor/SKILL.md`
- **Slash command:** `commands/aws/audit-cognito-user-pool.md`
- **Eval suite:** `skills/cognito-idp-user-pool-auditor/evals/evals.json`
- **Legacy test cases:** `skills/cognito-idp-user-pool-auditor/eval/test-cases.yaml`
