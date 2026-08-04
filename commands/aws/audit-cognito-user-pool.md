---
description: Audit a Cognito user pool configuration for MFA enforcement, password policy strength, app-client auth-flow safety (SRP vs password vs admin), OAuth flow exposure (implicit vs code+PKCE), token validity, PreventUserExistenceErrors, Advanced Security Features mode, and deletion protection.
nl_triggers:
  - "is this Cognito user pool secure"
  - "audit my Cognito pool"
  - "check MFA enforcement"
  - "password policy strength"
  - "app client auth flows"
  - "OAuth implicit flow"
  - "PreventUserExistenceErrors"
  - "AdvancedSecurityMode"
  - "token revocation"
  - "refresh token validity"
  - "account takeover risk"
  - "user enumeration"
  - "hosted UI security"
  - "ADMIN_NO_SRP_AUTH"
  - "ALLOW_ADMIN_USER_PASSWORD_AUTH"
  - "USER_SRP_AUTH vs USER_PASSWORD_AUTH"
  - "Cognito identity provider audit"
  - "harden my user pool"
routes_to: cognito-idp-user-pool-auditor
---

# /aws:audit-cognito-user-pool

Activate the `cognito-idp-user-pool-auditor` skill and classify one or more
Cognito user pool configurations against identity-security best practices.

## What it does

Reads a Cognito user pool configuration (pool-level settings + app-client
settings, pasted inline or read from `describe-user-pool` /
`describe-user-pool-client` output) and applies the 4-step classification
logic in precedence order:

1. **INSECURE** (CRITICAL) — any critical deficiency:
   - MFA OFF + weak password policy (Rule 1a).
   - OAuth implicit flow enabled (Rule 1b) — token leakage.
   - PreventUserExistenceErrors: LEGACY (Rule 1c) — user enumeration.
   - Admin auth flow on public client (Rule 1d).
   - No MFA + no ASF (Rule 1e) — zero adaptive defense.
2. **WEAK** (HIGH) — missing important hardening:
   - MFA optional (Rule 2a), non-SRP auth flow (Rule 2d), long refresh
     tokens (Rule 2e), ASF not enforced (Rule 2f), admin auth flow on
     confidential client (Rule 2g), insecure OAuth redirects (Rule 2h).
3. **ADEQUATE** (MODERATE) — MFA enforced but defense-in-depth gaps:
   - ASF in AUDIT mode (Rule 3a), password length 8-11 (Rule 3b),
     SMS-only MFA (Rule 3e), USER_PASSWORD_AUTH alongside SRP (Rule 3d).
4. **OK** (LOW) — all controls met (MFA ON TOTP, 12+ char password, ASF
   ENFORCED, SRP-only, code flow, token revocation, deletion protection).

Emits a deterministic VERDICT per pool:

```text
USER POOL: <name>
VERDICT: INSECURE | WEAK | ADEQUATE | OK
REASON: <1-2 sentences citing the specific rule and config>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

## When to invoke

Paste a Cognito user pool configuration and ask any of:

- "is this user pool secure?"
- "check MFA enforcement"
- "audit my app client auth flows"
- "is the OAuth configuration safe?"
- "harden this pool before production"
- "what's the account-takeover risk?"

A bare pool name or `user-pool-id` + any audit verb ("audit this pool",
"check this IdP") also routes here via the orchestrator.

## Inputs

- A Cognito user pool configuration: pool-level settings
  (`MfaConfiguration`, `EnabledMfas`, `PasswordPolicy`,
  `UserPoolAddOns.AdvancedSecurityMode`, `DeletionProtection`) and at
  least one app client's settings (`ExplicitAuthFlows`, `GenerateSecret`,
  `PreventUserExistenceErrors`, `EnableTokenRevocation`,
  `RefreshTokenValidity`, `AllowedOAuthFlows`, `CallbackURLs`).
- Optional: multiple app clients (the skill aggregates to the worst
  client verdict).
- Optional: `AccountRecoverySetting`, `LambdaConfig`,
  `AdminCreateUserConfig` for additional context.

## Outputs

- One VERDICT block per pool (multi-client pools aggregate to the worst
  client verdict).
- Specific remediation: CLI commands for MFA enforcement, password policy
  updates, auth-flow changes, OAuth flow fixes, ASF enablement.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Cognito Identity).
- `skills/cognito-idp-user-pool-auditor/SKILL.md` for the full
  classification logic, auth-flow strength matrix, OAuth flow strength
  matrix, and pre-flight safety checks.
