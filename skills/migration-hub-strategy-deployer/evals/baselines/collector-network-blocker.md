# Baseline (no-skill) response: collector-network-blocker

This file captures what a generic assistant produces WITHOUT the
migration-hub-strategy-deployer skill loaded.

---

The Collector is registered but not reporting data. This could be a
network issue. Check that the Collector VM can reach AWS on port 443.

If there's a firewall blocking the connection, you'll need to open it.
The Collector needs to upload data to the Migration Hub service in your
home region.

You could also try restarting the Collector VM to see if that resolves
the issue.
