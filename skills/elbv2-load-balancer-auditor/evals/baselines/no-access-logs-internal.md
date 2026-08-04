# Baseline (no-skill) response: no-access-logs-internal

This file captures what a generic assistant produces WITHOUT the
elbv2-load-balancer-auditor skill loaded.

---

Access logs are disabled on this internal ALB. Without access logs, you
won't have request-level data for troubleshooting or security
investigations. You should enable access logs by configuring an S3 bucket
for log delivery.

The TLS policy is good and the security group is properly restricted to
the internal network range.
