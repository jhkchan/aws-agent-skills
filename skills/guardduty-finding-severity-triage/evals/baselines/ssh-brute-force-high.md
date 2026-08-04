# Baseline (no-skill) response: ssh-brute-force-high

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-severity-triage skill loaded — the contrast that proves
the skill adds the brute-force escalation from MEDIUM to HIGH.

---

This finding shows that an EC2 instance was targeted by SSH brute force
attacks. There were 240 failed login attempts from IP 203.0.113.55
within 5 minutes.

The severity is 7.0, which is medium. This is concerning but the attacks
appear to have failed.

You should check whether any of the login attempts succeeded. You may
also want to restrict SSH access to known IP addresses and consider
using AWS Systems Manager Session Manager instead of SSH.
