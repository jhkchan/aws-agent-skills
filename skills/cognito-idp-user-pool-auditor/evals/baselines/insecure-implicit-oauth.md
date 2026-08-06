# Baseline (no-skill) — insecure-implicit-oauth

> This is the response a model produces **without** the skill definition.
> It lacks the ordered classification framework, rule citations, and
> severity matrix. Generated for with-skill-vs-baseline comparison.

---

Your pool looks mostly well-configured — MFA is ON with TOTP, the password
policy is strong (12 characters with all complexity requirements), Advanced
Security Features are ENFORCED, and the app client uses SRP auth.

However, I notice the OAuth configuration uses the `implicit` flow. This
means access tokens are returned directly in the URL fragment rather than
being exchanged via a back-channel request. While this is convenient for
single-page applications, it does expose the token in the browser URL. You
might want to consider switching to the authorization code flow for better
security.

Overall this pool is in good shape with one area to improve — the OAuth
flow configuration.
