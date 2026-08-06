# Baseline (no-skill) — weak-admin-auth-flow

> This is the response a model produces **without** the skill definition.
> It lacks the ordered classification framework, rule citations, and
> severity matrix. Generated for with-skill-vs-baseline comparison.

---

This pool has MFA set to OPTIONAL with TOTP available, a strong password
policy (12 characters, all complexity), and SRP authentication. Advanced
Security Features are OFF, which means no adaptive threat protection.

I notice the OAuth callback URLs include an HTTP URL
(`http://app.enterprise.example.com/callback`) and a wildcard subdomain
(`https://*.enterprise.example.com/callback`). HTTP URLs transmit the
authorization code unencrypted, and wildcard subdomains could allow any
subdomain to receive the code.

You should make MFA mandatory, enable ASF, and fix the callback URLs to use
HTTPS only without wildcards. The pool is reasonably configured but has
several security gaps to address.
