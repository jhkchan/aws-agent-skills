# Baseline (no-skill) response: console-login-anomalous

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-severity-triage skill loaded — the contrast that proves
the skill adds the MFA-verification and documented-change-window reasoning.

---

This finding shows that the IAM user jacky.chan logged into the AWS
console from Lagos, Nigeria, which is an unusual location for this user
(usually Singapore or Hong Kong). The severity is 5.0 (medium).

This could indicate a compromised credential or legitimate travel.
Since MFA was used, it is somewhat less likely to be malicious.

You should contact jacky.chan to verify whether they actually logged
in from Nigeria. If they did not, you should deactivate their access
keys and reset their password immediately.
