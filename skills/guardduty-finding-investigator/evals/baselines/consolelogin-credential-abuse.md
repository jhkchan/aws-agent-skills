# Baseline (no-skill) response: consolelogin-credential-abuse

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-investigator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, finding-type-driven probe order).

---

A ConsoleLogin finding from a new location usually means the user is
travelling. Check with the user — if they logged in from a new country
recently, this is expected. Otherwise, you may want to reset their
password.

If alice says she didn't log in, you should disable her account and
rotate her credentials. Make sure MFA is enabled for all your IAM
users to prevent this kind of thing.
