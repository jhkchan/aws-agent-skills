# Eval prompt: vpc-cni-ip-exhaustion

Diagnose the EKS node group issue for the following cluster. Walk the
node-state-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: 12 pods are stuck Pending with "FailedScheduling: 0/5 nodes
are available: insufficient IP addresses." All 5 nodes are Ready.

```text
ClusterName: prod-cluster
NodeGroupName: prod-ng-1
KubernetesVersion: "1.30"
InstanceTypes: ["m5.large"]
Subnets: ["subnet-private-a", "subnet-private-b"]
ScalingConfig: { minSize: 3, desiredSize: 5, maxSize: 10 }

kubectl get nodes:
  ip-10-0-10-10.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-10-11.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-11-10.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-11-11.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-10-12.ec2.internal   Ready    <none>   45h   v1.30.0

kubectl describe node ip-10-0-10-10.ec2.internal:
  Allocatable:
    pods: 29
  Allocated resources:
    (All 29 pod slots allocated)

Subnet context:
  subnet-private-a: CIDR 10.0.10.0/24,
    AvailableIpAddressCount: 3
  subnet-private-b: CIDR 10.0.11.0/24,
    AvailableIpAddressCount: 1

VPC CNI config:
  aws-node DaemonSet: Running (3/3)
  WARM_ENI_TARGET: 1 (default)
  ENABLE_PREFIX_DELEGATION: false

kubectl get pods -A (sample):
  app-pod-7b4   Pending   0/1   0   15m
  app-pod-7b5   Pending   0/1   0   15m
```

All nodes are Ready with available CPU and memory. The issue is
specifically that pods cannot get IP addresses. Distinguish between
insufficient CPU/memory scheduling and IP exhaustion.
