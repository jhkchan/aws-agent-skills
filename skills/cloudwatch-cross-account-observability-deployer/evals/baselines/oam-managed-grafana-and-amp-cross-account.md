# Baseline (no-skill) response: oam-managed-grafana-and-amp-cross-account

This file captures what a generic assistant produces WITHOUT the
cloudwatch-cross-account-observability-deployer skill loaded.

---

To wire Grafana, add a CloudWatch data source in the Grafana
console and point it at the monitoring account. For AMP, add a
Prometheus data source with the workspace URL. You may need to
create IAM roles so Grafana can read the data.
