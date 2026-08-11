# Cluster Mode and Edge Compute — Snowball Edge Deployer

Deep reference on cluster mode (5-10 node clusters, quorum, node
failure tolerance), Lambda functions on Snowball Edge, EKS Anywhere
deployment, and long-term rental. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Cluster mode fundamentals

### What cluster mode does

Cluster mode connects 5-10 Snowball Edge devices into a single
logical entity for COMPUTE resiliency. If one device fails, the
cluster continues operating.

```text
Cluster vs standalone:
  Standalone (1 device):
    ├── Single point of failure
    ├── Suitable for: data transfer (temporary)
    └── No HA guarantees

  Cluster (5-10 devices):
    ├── Fault-tolerant compute
    ├── Quorum-based: majority of nodes must be alive
    ├── Suitable for: edge computing, EKS Anywhere
    └── 5-node cluster tolerates 2 node failures
```

### Quorum rules

| Cluster size | Tolerated failures | Min nodes alive | Use case |
|---|---|---|---|
| 5 | 2 | 3 | Minimum for EKS Anywhere; small edge deployments |
| 7 | 3 | 4 | Medium edge deployments with more headroom |
| 10 | 5 | 5 | Maximum cluster size; large edge deployments |

### Cluster requirements

- All nodes must be the SAME device type (all Storage Optimized, or
  all Compute Optimized).
- All nodes must be unlocked and on the SAME network (mutual network
  visibility).
- Nodes should be on the same subnet for lowest latency.
- Each node needs its own manifest and unlock code.

## Cluster setup procedure

### Step 1: Create jobs for each node

```bash
for i in $(seq 1 5); do
  aws snowball create-job \
    --job-type LOCAL_USE \
    --snowball-type EDGE_COMPUTE_OPTIMIZED \
    --address-id addr-cluster01 \
    --description "Cluster node $i" \
    --region us-east-1
done
```

### Step 2: Unlock all nodes

```bash
# Each node has its own manifest and unlock code
for NODE_IP in 192.168.1.{100..104}; do
  snowballEdge unlock-device \
    --device-ip-address $NODE_IP \
    --manifest-file manifest-$NODE_IP.bin \
    --unlock-code XXXX-XXXX-XXXX \
    --endpoint https://$NODE_IP:9091
done
```

### Step 3: Verify cluster status

```bash
snowballEdge describe-cluster \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091
```

### Step 4: Start cluster services

```bash
# Start NFS on the cluster
snowballEdge start-service \
  --service-id nfs \
  --device-ip-address 192.168.1.100 \
  --manifest-file manifest-192.168.1.100.bin \
  --unlock-code XXXX-XXXX-XXXX \
  --endpoint https://192.168.1.100:9091
```

## Lambda functions on Snowball Edge

### Deploy Lambda functions

Compute Optimized and Snowcone devices support Lambda functions for
edge processing. Functions are pre-deployed from the AWS Lambda
service before the device ships.

```bash
# Create a Lambda function mapping on the device
snowballEdge create-function \
  --function-arn arn:aws:lambda:us-east-1:123456789012:function:edge-processor \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091

# List deployed functions
snowballEdge list-functions \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091

# Invoke a function
snowballEdge invoke-function \
  --function-arn arn:aws:lambda:us-east-1:123456789012:function:edge-processor \
  --payload '{"key":"value"}' \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091
```

### Lambda on Snowball use cases

- IoT data filtering and aggregation at edge sites.
- Image/video processing (e.g., resizing, format conversion).
- ML inference with pre-trained models (CPU-based).
- Data validation and transformation before upload.
- Custom logging and monitoring.

### Limitations

- Functions must be deployed BEFORE the device ships (via the job
  configuration).
- Functions cannot be updated on the device after deployment.
- Cold starts may take longer than cloud Lambda.
- Memory and execution time limits apply.

## EKS Anywhere on Snowball

### Prerequisites

- Minimum 5 Compute Optimized devices in cluster mode.
- All nodes on the same network with mutual visibility.
- EKS Anywhere cluster configuration prepared.

### Deployment overview

```text
EKS Anywhere on Snowball:
  1. Create 5+ LOCAL_USE jobs (Compute Optimized)
  2. Receive and unlock all devices
  3. Form cluster (all nodes same network)
  4. Deploy EKS Anywhere cluster spec
  5. EKS Anywhere manages Kubernetes lifecycle on the cluster
  6. Applications run as Kubernetes workloads
```

### EKS Anywhere cluster spec (example)

```yaml
apiVersion: anywhere.eks.amazonaws.com/v1alpha1
kind: Cluster
metadata:
  name: snowball-eks-cluster
spec:
  clusterNetwork:
    pods:
      cidrBlocks: ["10.244.0.0/16"]
    services:
      cidrBlocks: ["10.96.0.0/12"]
  controlPlaneConfiguration:
    count: 3  # 3 control plane nodes for HA
  workerNodeGroupConfigurations:
    - count: 2  # 2 worker nodes
  snowball:
    clusterName: snowball-edge-cluster
```

### EKS Anywhere management

- EKS Anywhere provides a management cluster that manages the
  workload cluster on Snowball.
- Upgrades require planning — download new EKS Anywhere bundles,
  apply to the management cluster.
- The cluster persists as long as the devices are powered and
  networked. If a device fails, replace it and rejoin the cluster.

## Long-term rental

### 1-year and 3-year terms

For persistent edge deployments, Snowball Edge devices can be rented
for 1-year or 3-year terms. This is cost-effective for:

- Continuous IoT processing at remote sites.
- ML inference at edge locations without data center infrastructure.
- EKS Anywhere clusters for edge applications.
- Data collection and buffering at sites with intermittent connectivity.

### Create a long-term rental job

```bash
aws snowball create-job \
  --job-type LOCAL_USE \
  --snowball-type EDGE_COMPUTE_OPTIMIZED \
  --address-id addr-edge-site \
  --description "Edge compute - 1 year rental" \
  --shipping-option NEXT_DAY \
  --region us-east-1
```

### Cost comparison

| Model | Upfront | Best for |
|---|---|---|
| On-demand (per-job) | Low per job | One-time data migration |
| 1-year rental | Medium | Persistent edge compute (12 months) |
| 3-year rental | Highest upfront, lowest per-month | Long-term edge deployments (36 months) |

For continuous edge computing lasting > 6 months, long-term rental
is more cost-effective than repeated on-demand jobs.
