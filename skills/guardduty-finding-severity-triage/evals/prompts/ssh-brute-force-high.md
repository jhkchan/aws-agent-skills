# Eval: ssh-brute-force-high

**Expected verdict:** HIGH
**Difficulty:** medium
**Branch:** Step 3 — brute-force threat-category escalation to HIGH

## Prompt

Triage this GuardDuty finding. Emit the standard VERDICT block (FINDING,
VERDICT, REASON, REMEDIATION).

```
Finding name: ssh-brute-force-high
Finding type: UnauthorizedAccess:EC2/SSHBruteForce
Severity: 7.0
Title: SSH Brute Force attacks against EC2 instance
Description: 240 failed SSH login attempts from a single external IP within 5 minutes.
Resource type: EC2 Instance
Resource: i-0prodapp9988 (production application server)
Action type: NETWORK_CONNECTION
Source IP: 203.0.113.55 (external, unknown reputation)
Count: 240
Confidence: HIGH
Context: Production application server with SSH port 22 open to 0.0.0.0/0
in security group sg-prodapp.
```
