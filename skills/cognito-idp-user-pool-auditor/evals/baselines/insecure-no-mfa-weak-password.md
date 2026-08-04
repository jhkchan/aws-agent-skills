# Baseline (no-skill) — insecure-no-mfa-weak-password

> This is the response a model produces **without** the skill definition.
> It lacks the ordered classification framework, rule citations, and
> severity matrix. Generated for with-skill-vs-baseline comparison.

---

Looking at your Cognito user pool configuration, there are several security
concerns:

1. **MFA is OFF** — Multi-factor authentication is not enabled. This means
   users only need a password to log in.

2. **Password policy is weak** — The minimum length is only 6 characters
   with no complexity requirements (no uppercase, lowercase, numbers, or
   symbols required). This makes passwords easy to brute-force.

3. **Advanced Security Features are OFF** — There's no adaptive threat
   protection or compromised credential detection.

4. **The app client has no secret** and uses `ALLOW_USER_PASSWORD_AUTH`,
   which sends the password directly to the API.

5. **Token revocation is disabled**, so stolen tokens can't be revoked.

I'd recommend enabling MFA, strengthening the password policy, and turning
on Advanced Security Features. This pool has significant security weaknesses.
