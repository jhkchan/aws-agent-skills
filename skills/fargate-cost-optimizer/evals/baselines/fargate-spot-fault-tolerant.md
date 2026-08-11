# Baseline (no-skill) response: fargate-spot-fault-tolerant

This file captures what a generic assistant produces WITHOUT the
fargate-cost-optimizer skill loaded.

---

Since your workload processes SQS messages and is stateless, you could
use Fargate Spot to save money. Spot instances are cheaper but can be
interrupted. Since your messages go back to the queue when a task is
killed, this should work fine.

You can set up a capacity provider in ECS to mix Spot and On-Demand.
Try adding the FargateSpot capacity provider to your cluster.
