# Baseline (no-skill) response: app-instance-endpoint-not-cluster

---

Your Aurora cluster failed over. The writer endpoint should have
updated automatically. Since the application is getting read-only
errors, it might be connecting to a reader instance.

Check which instance the application is connecting to. You may need
to update the connection string to point to the cluster endpoint
instead of an individual instance endpoint.
