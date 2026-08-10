# Baseline (no-skill) response: fargate-vs-ec2-scheduling-mismatch

This file captures what a generic assistant produces WITHOUT the
eks-cost-optimizer skill loaded.

---

Your dev cluster is running 3 m5.large nodes with only 2 pods each, which
is very low utilization. You should reduce the node count or consider
using Fargate for these dev workloads since they're sporadic.

Fargate might be cheaper for dev workloads since you only pay for what
you use per pod. With 6 pods requesting 0.5 vCPU and 1 GB each, Fargate
could be a good fit. You should compare the costs to see which is cheaper.
