# Baseline (no-skill) — captcha-atp-login-protection

> This is the response a model produces **without** the skill definition.
> It knows CAPTCHA exists but misses the ATP ManagedRuleGroupConfigs
> syntax (LoginPath, PayloadType, UsernameField, PasswordField), the
> OverrideAction Count vs None distinction for managed rule groups, and
> the client-side aws-waf JavaScript SDK integration requirement.

---

Create a WAF for your auth service:

```bash
aws wafv2 create-web-acl \
  --name auth-service-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --region us-east-1
```

Add a CAPTCHA rule on /signup and the ATP rule group for login
protection. Enable logging and associate with your ALB.
