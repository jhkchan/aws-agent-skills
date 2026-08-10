# Baseline (no-skill) response: pilot-light-aurora-global

This file captures what a generic assistant produces WITHOUT the
dr-failover-automator skill loaded.

---

To set up pilot-light DR for your three-tier app, you'll want to use
Aurora Global Database to replicate from us-east-1 to us-west-2. Set up
a Route 53 health check on your primary ALB and configure a failover
record to point at the secondary when the primary is unhealthy.

For compute, keep an Auto Scaling Group in us-west-2 with a desired
capacity of 0 that scales up on failover. Use launch templates to
pre-configure the instances.

When failover occurs, promote the Aurora secondary to primary using the
AWS CLI. Then update Route 53 to point at the secondary ALB. You can
automate this with a Lambda function triggered by the health check
alarm.

Test the failover periodically to make sure it works.
