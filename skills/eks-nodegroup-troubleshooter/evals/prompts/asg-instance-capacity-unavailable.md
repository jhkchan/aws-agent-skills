# Eval prompt: asg-instance-capacity-unavailable

Diagnose the EKS node group issue for the following cluster. Walk the
node-state-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: the node group `prod-ng-1` cannot scale from 3 to 5 nodes.
The ASG desired capacity was raised to 5 but only 3 instances are
running. The cluster autoscaler shows "scale-up failed."

```text
ClusterName: prod-cluster
NodeGroupName: prod-ng-1
InstanceTypes: ["m5.large"]
Subnets: ["subnet-private-a (us-east-1a)", "subnet-private-b (us-east-1b)"]
ScalingConfig: { minSize: 3, desiredSize: 5, maxSize: 10 }
CurrentRunningInstances: 3 (out of desired 5)

ASG Activity (most recent):
  StatusCode: Failed
  StatusMessage: "Launching a new EC2 instance. Status Reason:
    Insufficient instance capacity. us-east-1a."
  Cause: "At 2026-08-11T14:30:00Z a user request created a
    launch configuration change."

aws eks describe-nodegroup health:
  issues: []

kubectl get nodes:
  (3 Ready nodes, all in us-east-1b subnet)

kubectl get events:
  Warning  FailedScheduling  15 pods Pending (insufficient nodes)
```

The ASG is configured to span two AZs. The failure is specific to
us-east-1a capacity. Distinguish between a scaling config issue and
an AWS-side capacity issue.
