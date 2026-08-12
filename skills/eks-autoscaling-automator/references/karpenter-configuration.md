# Karpenter Configuration Reference

Supplementary reference for the EKS Autoscaling Automator skill. Use
when deploying Karpenter, configuring NodePools/EC2NodeClasses,
troubleshooting consolidation, or tuning disruption budgets.

## Karpenter v1 API migration guide

Karpenter v1 introduced breaking changes from v0.3x:

| v0.3x (old) | v1 (new) | Notes |
|---|---|---|
| `Provisioner` | `NodePool` | API group: `karpenter.sh/v1` |
| `AWSNodeTemplate` | `EC2NodeClass` | API group: `karpenter.k8s.aws/v1` |
| `spec.provider` | `spec.template.spec.nodeClassRef` | Reference to EC2NodeClass by name |
| `spec.providerRef` | `spec.template.spec.nodeClassRef` | Same |
| `consolidationPolicy: WhenUnderutilized` | `consolidationPolicy: WhenEmptyOrUnderutilized` | Renamed |
| `spec.consolidation.enabled` | N/A (always enabled, controlled by policy) | Removed toggle |
| `ttlSecondsUntilExpired` | `deletionPolicy: Delete` | TTL replaced by explicit deletion policy |
| `ttlSecondsAfterEmpty` | `consolidateAfter: 30s` | Part of disruption config |

## NodePool anatomy

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: <name>
spec:
  template:
    metadata:
      labels: {}          # Labels applied to all nodes from this pool
    spec:
      requirements: []    # Instance-type/AZ/capacity constraints
      nodeClassRef:       # Reference to EC2NodeClass
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: <name>
      taints: []          # Taints applied to nodes (for dedicated workloads)
      startupTaints: []   # Taints removed after node is ready
  limits:                 # Hard capacity ceiling
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: <WhenEmpty | WhenEmptyOrUnderutilized>
    consolidateAfter: <duration>
    budgets: []
  deletionPolicy: <Delete | Retain>
```

## Requirement operators

| Operator | Meaning | Example |
|---|---|---|
| `In` | Value must be in the list | `values: ["c5.large", "m5.large"]` |
| `NotIn` | Value must NOT be in the list | `values: ["t3.micro"]` |
| `Gt` | Numeric value must be greater than | `values: ["5"]` (generation > 5) |
| `Lt` | Numeric value must be less than | `values: ["8"]` |
| `Exists` | Key must exist (value ignored) | N/A |
| `DoesNotExist` | Key must NOT exist | N/A |

## Well-known requirement keys

| Key | Description | Example values |
|---|---|---|
| `karpenter.k8s.aws/instance-category` | Instance family first letter | `c`, `m`, `r`, `t`, `g` |
| `karpenter.k8s.aws/instance-family` | Full instance family | `c5`, `m5`, `c6i`, `g4dn` |
| `karpenter.k8s.aws/instance-generation` | Generation number | `3`, `4`, `5`, `6`, `7` |
| `karpenter.k8s.aws/instance-cpu` | vCPU count | `2`, `4`, `8`, `16`, `32` |
| `karpenter.k8s.aws/instance-memory` | Memory in GiB | `4`, `8`, `16`, `32` |
| `karpenter.k8s.aws/instance-gpu-count` | GPU count | `0`, `1`, `4`, `8` |
| `karpenter.k8s.aws/instance-gpu-manufacturer` | GPU maker | `nvidia`, `amd` |
| `karpenter.k8s.aws/instance-hypervisor` | Hypervisor type | `nitro`, `xen` |
| `karpenter.k8s.aws/instance-local-nvme` | Local NVMe in GB | `0`, `900`, `3600` |
| `karpenter.k8s.aws/instance-network-bandwidth` | Network in Gbps | `1`, `10`, `25` |
| `karpenter.k8s.aws/instance-pods` | Max pods per node | `10`, `20`, `110`, `250` |
| `karpenter.k8s.aws/instance-size` | Size suffix | `large`, `xlarge`, `2xlarge` |
| `karpenter.sh/capacity-type` | Spot or on-demand | `spot`, `on-demand` |
| `topology.kubernetes.io/zone` | AZ | `us-east-1a`, `us-east-1b` |
| `kubernetes.io/arch` | CPU architecture | `amd64`, `arm64` |
| `kubernetes.io/os` | OS | `linux`, `windows` |
| `karpenter.sh/nodepool` | NodePool name (auto-set) | `<name>` |

## Disruption budget patterns

**Pattern 1: Constant rate (default production)**

```yaml
disruption:
  budgets:
    - nodes: "20%"
```

Allows Karpenter to disrupt up to 20% of nodes at any time.

**Pattern 2: Business-hours freeze**

```yaml
disruption:
  budgets:
    - nodes: "20%"
    - schedule: "0 9 * * Mon-Fri"
      duration: 8h
      nodes: "0"
```

Allows 20% disruption normally, but ZERO disruption during business
hours (Mon-Fri 09:00-17:00).

**Pattern 3: Maintenance window**

```yaml
disruption:
  budgets:
    - nodes: "0"
    - schedule: "0 2 * * Sat"
      duration: 4h
      nodes: "50%"
```

Freezes disruption normally, allows 50% during a Saturday 02:00-06:00
maintenance window.

**Budget evaluation:** Karpenter evaluates budgets in order. The first
matching budget (by schedule) wins. If no schedule matches, the
default (non-scheduled) budget applies. Multiple non-scheduled budgets
are not supported — use one default and multiple scheduled overrides.

## EC2NodeClass configuration

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  # AMI selection — use alias for always-latest, or specific AMI ID
  amiSelectorTerms:
    - alias: al2023@latest           # Amazon Linux 2023, latest EKS-optimized
    # - id: ami-0abc123def            # Specific AMI (pin for reproducibility)
    # - tags:
    #     Name: my-custom-ami

  # Subnet selection — Karpenter picks from matching subnets
  subnetSelectorTerms:
    - tags:
        Name: my-cluster-private-*
    # - id: subnet-0abc123def         # Specific subnet

  # Security group selection
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-cluster: owned

  # IAM role for the node (must match the EKS node IAM role)
  role: KarpenterNodeRole-my-cluster

  # Custom user data (merged with Karpenter's bootstrap)
  userData: |
    #!/bin/bash
    echo "custom setup" >> /tmp/setup.log

  # Block device mappings (EBS volumes)
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        kmsKeyID: arn:aws:kms:us-east-1:111111111111:key/abc-123
        deleteOnTermination: true

  # Detailed monitoring
  detailedMonitoring: true

  # Tags applied to EC2 instances launched by Karpenter
  tags:
    Team: platform
    CostCenter: engineering
```

## Consolidation troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Nodes never consolidated | `consolidationPolicy: WhenEmpty` (only removes empty nodes) | Switch to `WhenEmptyOrUnderutilized` |
| Too many disruptions | No disruption budget or budget too permissive | Add `disruption.budgets` with `nodes: "10%"` |
| Pods stuck Pending after consolidation | Not enough capacity for rescheduled pods | Increase NodePool `limits` or add overprovisioning |
| Consolidation oscillation | Pods keep scheduling and descheduling | Increase `consolidateAfter` (e.g., `5m`) |
| Spot nodes constantly replaced | Single instance family, capacity reclaimed | Diversify across 4+ instance families |

## Karpenter metrics

Key Prometheus metrics exposed by Karpenter:

| Metric | Description |
|---|---|
| `karpenter_pods_state` | Current state of pods (Pending, Bound, etc.) |
| `karpenter_nodes` | Total nodes managed by Karpenter |
| `karpenter_nodeclaims` | NodeClaim count by state (Pending, Ready, etc.) |
| `karpenter_disruption_actions_total` | Disruption actions taken (consolidation, spot replacement) |
| `karpenter_allocation_duration_seconds` | Time to allocate a pod to a node |
| `karpenter_deprovisioning_actions_performed_total` | Deprovisioning actions (delete, replace) |

**Alert: pods Pending too long**

```yaml
- alert: KarpenterPodsPending
  expr: max_over_time(karpenter_pods_state{node_name=""}[5m]) > 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Pods have been Pending for > 5 minutes — possible capacity issue"
```
