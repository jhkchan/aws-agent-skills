# Baseline (no-skill) — weak-optional-mfa

> This is the response a model produces **without** the skill definition.
> It lacks the ordered classification framework, rule citations, and
> severity matrix. Generated for with-skill-vs-baseline comparison.

---

Your pool has a reasonable configuration but a few areas for improvement:

1. **MFA is OPTIONAL** — Users can enable MFA but aren't required to. You
   should consider making it mandatory for better security.

2. **Password policy** requires 8 characters with uppercase, lowercase, and
   numbers, but symbols are not required. Consider adding symbol
   requirements.

3. **Refresh token validity is 90 days** — This is fairly long. Shorter
   token validity (e.g., 30 days) would be more secure.

4. **Advanced Security is in AUDIT mode** — This logs suspicious activity
   but doesn't block it. Consider switching to ENFORCED mode.

The pool uses SRP authentication which is good, and the app client has a
secret. Overall this is a decent configuration with some room for
hardening.
