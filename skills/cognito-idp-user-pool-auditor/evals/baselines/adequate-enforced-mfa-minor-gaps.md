# Baseline (no-skill) — adequate-enforced-mfa-minor-gaps

> This is the response a model produces **without** the skill definition.
> It lacks the ordered classification framework, rule citations, and
> severity matrix. Generated for with-skill-vs-baseline comparison.

---

Your pool looks fairly secure:

1. **MFA is ON** — Good, MFA is enforced for all users.

2. **Password policy** requires 10 characters with all complexity rules.
   This is decent, though you could bump it to 12+ for extra security.

3. **Advanced Security is in AUDIT mode** — It's monitoring but not blocking
   suspicious activity. Consider moving to ENFORCED when you're confident
   there are no false positives.

4. **The app client uses SRP** with a secret, PreventUserExistenceErrors is
   enabled, and token revocation is on. The OAuth code flow with HTTPS
   callbacks is correct.

5. **MFA is SMS-only** — SMS MFA works but is vulnerable to SIM-swapping
   attacks. Consider enabling TOTP (software token) MFA as well, which is
   more secure.

Overall this is a solid configuration. The main improvements would be
enabling TOTP MFA and transitioning ASF to ENFORCED mode.
