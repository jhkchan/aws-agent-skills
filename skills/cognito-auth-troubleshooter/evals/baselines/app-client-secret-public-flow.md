# Baseline (no-skill) response: app-client-secret-public-flow

This file captures what a generic assistant produces WITHOUT the
cognito-auth-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

The error invalid_client means your client credentials are wrong. Check
that you're passing the correct client_id and client_secret in your
API call. You might need to regenerate the client secret in the Cognito
console and update your application configuration.

Also verify that your app client ID is correct and that you're hitting
the right User Pool endpoint.
