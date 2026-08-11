# Baseline (no-skill) response: oam-cross-account-application-signals-gap

This file captures what a generic assistant produces WITHOUT the
cloudwatch-cross-account-observability-deployer skill loaded.

---

If Application Signals metrics are missing in the monitoring
account, check that the link is attached. The OAM link should
transport Application Signals data automatically once the service
is running. You might need to wait longer, or check that the ECS
task has the right IAM permissions. Application Signals should
work once the workload is detected.
