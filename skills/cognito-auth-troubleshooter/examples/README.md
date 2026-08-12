# Example usage: cognito-auth-troubleshooter

A walkthrough showing the skill diagnosing a hosted UI redirect mismatch
that mimics a broken authentication backend, demonstrating the
symptom-to-layer triage, the PUBLIC-vs-CONFIDENTIAL client check, the
evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the callback-URL
configuration root cause.

## Input (user prompt)

> Users are reporting a redirect_mismatch error when trying to log in
> through our Cognito hosted UI. They enter their credentials on the
> Cognito login page and then see an error page. This started after we
> deployed a new frontend build that changed the callback path.

```text
UserPoolId: us-east-1_AbCdEf123
AppClientId: 1ab2cd3ef4gh5ij6lmn7opq8rs
ClientName: web-app-client
AuthFlow: code grant (hosted UI /oauth2/authorize)
Domain: auth.example.com (Cognito custom domain)

App Client configuration:
  CallbackURLs: ["https://app.example.com/callback"]
  LogoutURLs: ["https://app.example.com/logout"]
  AllowedOAuthFlows: ["code"]
  AllowedOAuthScopes: ["openid", "email", "profile"]
  SupportedIdentityProviders: ["COGNITO"]
  ClientSecret: (null — PUBLIC client)
  ExplicitAuthFlows: ["ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"]

Application config (from frontend):
  redirect_uri: https://app.example.com/auth/callback
```

## Skill output

```text
TARGET: us-east-1_AbCdEf123 / client 1ab2cd3ef4gh5ij6lmn7opq8rs
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The application sends redirect_uri=https://app.example.com/auth/callback
  but the app client CallbackURLs lists only
  https://app.example.com/callback. The path /auth/callback is missing
  from the configured callback list. The new frontend build changed
  the callback path from /callback to /auth/callback without updating
  the Cognito app client configuration (Step 4).
LAYER: HOSTED_UI_REDIRECT
EVIDENCE:
  - Symptom: all users see redirect_mismatch error after entering
    credentials on the hosted UI. The browser address bar shows
    redirect_uri=https://app.example.com/auth/callback.
  - Probe: aws cognito-idp describe-user-pool-client returns
    CallbackURLs: ["https://app.example.com/callback"] — the path
    /auth/callback is absent. The application frontend is configured
    with redirect_uri=https://app.example.com/auth/callback.
  - Passing: ClientSecret is null (PUBLIC client, no secret mismatch);
    ExplicitAuthFlows includes ALLOW_USER_SRP_AUTH and
    ALLOW_REFRESH_TOKEN_AUTH (flows are correct); AllowedOAuthFlows
    includes "code" (code grant is enabled); no Lambda triggers
    configured (trigger error ruled out).
REMEDIATION:
  1. Add the correct callback URL to the app client:
     aws cognito-idp update-user-pool-client \
       --user-pool-id us-east-1_AbCdEf123 \
       --client-id 1ab2cd3ef4gh5ij6lmn7opq8rs \
       --callback-urls "https://app.example.com/auth/callback" "https://app.example.com/callback"
  2. Verify by navigating to the hosted UI authorize endpoint with
     redirect_uri=https://app.example.com/auth/callback — the redirect
     should succeed without error.
CONFIRM: Before updating the app client, emit and await:
  "CONFIRM: About to add https://app.example.com/auth/callback to
   CallbackURLs on client 1ab2cd3ef4gh5ij6lmn7opq8rs. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Identified the exact path difference.** A generic assistant says
   "check your redirect URI." The skill identifies the specific path
   difference: the application sends `/auth/callback` but Cognito has
   `/callback` — and traces it to the frontend deploy that changed the
   callback path.

2. **Ruled out the client secret.** A common misdiagnosis on hosted UI
   errors is to check the client secret. The skill confirms
   `ClientSecret: null` (PUBLIC client) and rules out `APP_CLIENT_SECRET`
   with positive evidence.

3. **Ruled out the auth flow.** The skill confirms `ExplicitAuthFlows`
   includes the required flows and `AllowedOAuthFlows` includes `code`
   grant, ruling out `AUTH_FLOW` as a cause.

4. **Recommended updating Cognito, not the app.** The new frontend path
   is the intended design. The fix is to update Cognito's `CallbackURLs`
   to match, not to revert the frontend change.

5. **Preserved both callback URLs in the fix.** The remediation adds
   the new URL while keeping the old one, ensuring backward
   compatibility during rollout.

## Slash-command invocation

```
/aws:troubleshoot-cognito-auth
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why users see redirect_mismatch on the hosted UI"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: cognito-auth-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the hosted UI flow:

```bash
# Confirm the callback URL is now listed
aws cognito-idp describe-user-pool-client \
  --user-pool-id us-east-1_AbCdEf123 \
  --client-id 1ab2cd3ef4gh5ij6lmn7opq8rs \
  --profile default --output json | jq '.CallbackURLs'

# Test the authorize endpoint directly
curl -sI "https://auth.example.com/oauth2/authorize?response_type=code&client_id=1ab2cd3ef4gh5ij6lmn7opq8rs&redirect_uri=https://app.example.com/auth/callback&scope=openid+email+profile" | head -5
```

Then monitor sign-in success rate for 1 hour to confirm the
redirect_mismatch count drops to zero.
