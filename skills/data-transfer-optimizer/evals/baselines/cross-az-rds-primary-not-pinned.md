# Baseline (no-skill) response: cross-az-rds-primary-not-pinned

---

You're paying $160/month in cross-AZ transfer. The RDS primary is
in us-east-1a but workers are spread across all three AZs. You
could pin the workers to us-east-1a to save the cross-AZ charges.

Just update the ASG to use only the us-east-1a subnet.
