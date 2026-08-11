# Baseline (no-skill) response: connectivity-sg-blocking-port-9094

This file captures what a generic assistant produces WITHOUT the
kafka-msk-troubleshooter skill loaded.

---

Your clients are timing out connecting to the Kafka brokers. The issue
might be network-related. Since port 9092 works but 9094 doesn't, there
could be a firewall or network configuration issue blocking the TLS port.

Try checking your VPC settings and security groups. You should also make
sure your client is using the correct bootstrap broker address and port.
Consider switching to a different port if TLS doesn't work, or verify
your TLS certificate configuration.
