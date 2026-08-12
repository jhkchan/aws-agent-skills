# Baseline (no-skill) response: saml-provider-cert-mismatch

This file captures what a generic assistant produces WITHOUT the
cognito-auth-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

The SAMLResponseDoesNotMatch error means the SAML response from Okta
doesn't match what Cognito expects. This could be a configuration issue
with your SAML provider. Check that the Okta metadata is correct and
that the certificate is valid.

You might need to re-import the SAML metadata from Okta into Cognito.
Also verify that the Okta SAML configuration matches the Cognito
settings.
