
<!-- Moved verbatim from SKILL.md (eks-nodegroup-troubleshooter) — progressive-disclosure restructure, lines 131-145 -->

## Expert heuristic — warm IP pool, version skew, ASG headroom

> **VPC CNI warm IP pool determines pod IP allocation cadence.** Key
> `aws-node` env vars:
> - `WARM_ENI_TARGET` (default 1): pre-allocate IPs for one full ENI.
> - `WARM_IP_TARGET`: pre-allocate exactly N free IPs.
> - `WARM_PREFIX_TARGET`: pre-allocate a /28 prefix (16 IPs per
>   delegation; requires prefix delegation mode).
>
> **Node group AMI K8s version MUST align with the control plane.** EKS
> supports skew of at most one minor version (kubelet ≤ API server + 1).
> A node group AMI behind the control plane produces NotReady nodes.
>
> **ASG capacity is the scaling safety net.** For cluster autoscaler /
> Karpenter, the ASG must have headroom (`minSize < maxSize`). If
> `maxSize == desiredCapacity`, scaling fails silently — the autoscaler
> logs "no nodes can be added" but the node group appears healthy.

<!-- Moved verbatim from SKILL.md (eks-nodegroup-troubleshooter) — progressive-disclosure restructure, lines 149-177 -->

## Configuration dependency graph

```
                    EKS Cluster
                   (kubernetesVersion,
                    endpoint, CA cert,
                    vpcConfig)
                        │
         ┌──────────────┼──────────────────┐
         ▼              ▼                  ▼
    managed node    VPC CNI            cluster autoscaler /
    group           (aws-node          Karpenter
    (amiType,       DaemonSet,            (scales ASG or
     instanceTypes, manages ENIs          provisions nodes)
     subnets,       and pod IPs;              │
     nodeRole,      needs IRSA role           ▼
     scalingConfig, with CNI policy)      ASG
     SGs)                │               (launch template,
         │                ▼                minSize, maxSize,
         ▼          node subnets           desiredCapacity)
    launch template  (AvailableIpAddr         │
    (user-data,      Count → IP pool;         ▼
     bootstrap.sh)   ENI limits per       EC2 instances
         │            instance type)       (kubelet, containerd,
         ▼                                node IAM role)
    node IAM role                            │
    (ECR pull, SSM,                          ▼
     CloudWatch)                        ECR repository
                                        (node role needs
                                         ecr:BatchGetImage)
```

