# Baseline (no-skill) response: hosted-ui-callback-mismatch

This file captures what a generic assistant produces WITHOUT the
cognito-auth-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

It looks like your redirect URI doesn't match. Check the redirect_uri
in your application and make sure it matches what's in Cognito. The
issue is probably that your app is sending a slightly different URL
than what Cognito expects.

You should update either your app or Cognito to make them match. Also
check that you're using HTTPS and that the domain is correct.
