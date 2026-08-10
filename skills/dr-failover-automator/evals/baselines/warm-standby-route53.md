# Baseline (no-skill) response: warm-standby-route53

This file captures what a generic assistant produces WITHOUT the
dr-failover-automator skill loaded.

---

For warm-standby DR, keep a scaled-down version of your application
running in us-west-2 at all times. Use Aurora Serverless v2 for cost
efficiency. Set up Route 53 failover records with health checks to
route traffic to the secondary when the primary is down.

You can also use Global Accelerator for faster failover. Configure the
traffic dials so the primary gets 100% and the secondary gets 0%.
Flip them on failover.

For the database, use Aurora Global Database to replicate from
us-east-1 to us-west-2. On failover, promote the secondary using
managed planned failover.

Automate the failover with a Lambda function or Step Functions state
machine. Test regularly with game-day drills.
