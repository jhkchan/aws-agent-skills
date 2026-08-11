# Baseline (no-skill) response: clb-to-alb-migration-savings

This file captures what a generic assistant produces WITHOUT the
elb-cost-optimizer skill loaded.

---

You should migrate your Classic Load Balancer to an Application Load
Balancer. ALBs are cheaper and support path-based routing and SNI,
which is what you need. The migration would save you a few dollars per
month on the hourly rate.

You'll need to create a new ALB, set up target groups and listeners,
and gradually move traffic over. Once the migration is complete, you
can delete the old CLB.
