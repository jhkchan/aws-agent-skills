# Baseline (no-skill) response: both-records-unhealthy-blocked

This file captures what a generic assistant produces WITHOUT the
route53-failover-operator skill loaded.

---

Both endpoints appear to be down. You should try restarting the
secondary service first since it is the failover target. Once the
secondary is healthy, traffic should automatically route to it.

You may also want to investigate why the primary went down. Check
your EC2 instance status or your application logs.
