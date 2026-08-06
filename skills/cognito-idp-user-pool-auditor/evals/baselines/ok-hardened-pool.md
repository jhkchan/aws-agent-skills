# Baseline (no-skill) — ok-hardened-pool

> This is the response a model produces **without** the skill definition.
> It lacks the ordered classification framework, rule citations, and
> severity matrix. Generated for with-skill-vs-baseline comparison.

---

This pool is very well-configured:

1. **MFA is ON** with TOTP (SOFTWARE_TOKEN_MFA) — enforced for all users.
2. **Password policy** requires 14 characters with all complexity rules and
   a 3-day temp password validity — excellent.
3. **Advanced Security is ENFORCED** — adaptive threat protection is active.
4. **The app client uses SRP** only (ALLOW_USER_SRP_AUTH +
   ALLOW_REFRESH_TOKEN_AUTH), has a secret, PreventUserExistenceErrors is
   ENABLED, token revocation is on.
5. **Refresh token validity is 7 days** — appropriately short.
6. **OAuth uses code flow** with HTTPS callback and logout URLs.
7. **Deletion protection is ACTIVE**.
8. **Account recovery** uses both verified email and phone number.

This pool meets security best practices across all dimensions. No
significant issues to report.
