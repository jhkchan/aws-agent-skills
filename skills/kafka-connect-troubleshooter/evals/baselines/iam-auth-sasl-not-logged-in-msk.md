# Baseline (no-skill) response: iam-auth-sasl-not-logged-in-msk

This file captures what a generic assistant produces WITHOUT the
kafka-connect-troubleshooter skill loaded.

---

Your connector can't authenticate to MSK. The error says
SASL_NOT_LOGGED_IN, which means authentication failed. Check that
your connector's IAM role has the right permissions to access the
Kafka cluster.

You might also want to verify that the bootstrap brokers are correct
and that TLS is properly configured.
