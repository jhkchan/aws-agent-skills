# Baseline (no-skill) response: timeout-sg-missing-rule

This file captures what a generic assistant produces WITHOUT the
rds-connectivity-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, OSI-aligned probe order).

---

Your application can't reach the RDS instance. The telnet hanging means
it's a network issue, not a database issue. Check the security group on
the RDS instance and make sure it allows port 3306 from your app server's
IP address. You might also want to check the NACL and route table.

Once you fix the network, the database should be reachable. You can try
adding a rule to allow 10.42.5.10/32 on port 3306.
