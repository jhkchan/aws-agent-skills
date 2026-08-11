# Baseline (no-skill) response: alb-consolidation-multi-path-routing

This file captures what a generic assistant produces WITHOUT the
elb-cost-optimizer skill loaded.

---

You have three ALBs serving subdomains of example.com. Since they're
all in the same VPC and you have a wildcard certificate, you could
combine them into a single ALB using host-based routing. This would
save you about $33/month from the per-hour charges of the two ALBs
you'd eliminate.

You'd need to set up listener rules for each hostname and point them
to the right target groups. Make sure to test everything before
deleting the old ALBs.
