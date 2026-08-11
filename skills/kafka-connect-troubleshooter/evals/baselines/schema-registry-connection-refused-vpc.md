# Baseline (no-skill) response: schema-registry-connection-refused-vpc

This file captures what a generic assistant produces WITHOUT the
kafka-connect-troubleshooter skill loaded.

---

Your connector can't reach the schema registry. The error says
"Connection refused." Make sure the schema registry is running and
that the URL in your connector config is correct.

You could try restarting the schema registry service or checking
that the IP address 10.50.10.20 is reachable.
