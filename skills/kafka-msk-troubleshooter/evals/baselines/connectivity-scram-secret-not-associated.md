# Baseline (no-skill) response: connectivity-scram-secret-not-associated

This file captures what a generic assistant produces WITHOUT the
kafka-msk-troubleshooter skill loaded.

---

Your Kafka client is failing SCRAM authentication. This usually means
the username or password is wrong. Make sure you have the correct
credentials configured in your client properties.

Check that your SCRAM credentials are properly set up in AWS Secrets
Manager and that your client is using the right SASL mechanism. You
might also want to verify the TLS configuration since SCRAM requires
a TLS transport.

If the password looks correct, try recreating the secret or restarting
your client application.
