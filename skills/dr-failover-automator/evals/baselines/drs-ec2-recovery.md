# Baseline (no-skill) response: drs-ec2-recovery

This file captures what a generic assistant produces WITHOUT the
dr-failover-automator skill loaded.

---

To use AWS Elastic Disaster Recovery (DRS) for your 20 EC2 instances,
install the DRS agent on each source server. The agent will continuously
replicate block-level changes to a staging area in us-west-2.

When failover is needed, use `aws drs start-recovery` to launch recovery
instances from the replicated data. Make sure you have launch templates
configured for each source server with the right instance type, subnet,
and security group.

You can run drills using the `--is-drill true` flag to test failover
without affecting production. Route 53 can handle DNS failover with
health checks.

Test your DRS setup regularly to make sure recovery instances launch
correctly.
