# Baseline (no-skill) response: identity-pool-unauth-role-trust

This file captures what a generic assistant produces WITHOUT the
cognito-auth-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

The NotAuthorizedException from GetCredentialsForIdentity suggests a
permissions issue. Check that your IAM roles have the right policies
attached. Make sure the unauthenticated role has the permissions it
needs and that the identity pool is configured to allow unauthenticated
identities.

You might also want to check if there are any SCPs or permission
boundaries blocking access.
