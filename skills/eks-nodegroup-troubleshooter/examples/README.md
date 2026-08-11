# Example usage: eks-nodegroup-troubleshooter

A walkthrough showing the skill diagnosing VPC CNI IP exhaustion,
demonstrating the node-state-driven triage, the warm IP pool
heuristic, the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and
the infrastructure-layer root cause.

## Input (user prompt)

> We have 12 pods stuck Pending in production. The error says
> "insufficient IP addresses" but all 5 nodes are Ready and have
> available CPU and memory. We can't figure out why pods won't
> schedule. Help us find the root cause.

```text
ClusterName: prod-cluster
NodeGroupName: prod-ng-1
KubernetesVersion: "1.30"
InstanceTypes: ["m5.large"]
Subnets: ["subnet-private-a", "subnet-private-b"]

kubectl get nodes:
  ip-10-0-10-10.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-10-11.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-11-10.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-11-11.ec2.internal   Ready    <none>   45h   v1.30.0
  ip-10-0-10-12.ec2.internal   Ready    <none>   45h   v1.30.0

kubectl describe node ip-10-0-10-10:
  Allocatable:
    cpu: 1930m, memory: 7174Mi, pods: 29
  Allocated resources:
    cpu: 1500m (77%), memory: 4096Mi (57%)
    (All 29 pod slots allocated)

Subnet context:
  subnet-private-a: CIDR 10.0.10.0/24, AvailableIpAddressCount: 3
  subnet-private-b: CIDR 10.0.11.0/24, AvailableIpAddressCount: 1

VPC CNI:
  aws-node DaemonSet: Running
  WARM_ENI_TARGET: 1 (default)
  ENABLE_PREFIX_DELEGATION: false
```

## Skill output

```text
TARGET: prod-cluster / prod-ng-1
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Pods are stuck Pending with "FailedScheduling: 0/5 nodes are
  available: insufficient IP addresses." The node subnets
  (subnet-private-a with 3 available IPs, subnet-private-b with 1
  available IP) are nearly exhausted. Each m5.large node can host 29
  pods (3 ENIs * 10 IPs each - 1 primary), and 5 nodes at capacity
  consume 145 IPs from the /24 subnets. The default WARM_ENI_TARGET=1
  pre-allocates IPs for one full ENI per node, accelerating exhaustion
  (Step 2).
ROOT_CAUSE: VPC_CNI_IP_EXHAUSTION
EVIDENCE:
  - Symptom: 12 pods Pending with "insufficient IP addresses"; all 5
    nodes Ready with available CPU (77%) and memory (57%).
  - Probe: aws ec2 describe-subnets returns AvailableIpAddressCount: 3
    for subnet-private-a and 1 for subnet-private-b.
  - Probe: kubectl describe node shows all nodes at max pods (29),
    with all ENI secondary IPs allocated.
  - Passing: nodes have available CPU and memory (not a resource
    scheduling issue); nodes are Ready (not a kubelet issue); no
    taints on any node (not a taint scheduling issue).
REMEDIATION:
  1. Enable prefix delegation to get 16 IPs per prefix instead of 1
     per secondary IP:
     kubectl set env ds aws-node -n kube-system \
       ENABLE_PREFIX_DELEGATION=true
  2. After CNI restarts on all nodes, create new wider subnets (/20)
     in the VPC and add them to the node group's subnet list:
     aws ec2 create-subnet --vpc-id <vpc-id> --cidr-block 10.0.20.0/20
     aws eks update-nodegroup-config --cluster-name prod-cluster \
       --nodegroup-name prod-ng-1 \
       --subnets <new-subnet-1> <new-subnet-2> --profile <p>
  3. Verify by watching pods transition from Pending to Running:
     kubectl get pods --watch
CONFIRM: Before updating, emit and await:
  "CONFIRM: About to enable prefix delegation on aws-node and/or add
   new subnets to prod-ng-1. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Identified IP exhaustion as the root cause, not CPU/memory.** A
   generic assistant sees "insufficient" and assumes resources. The
   skill reads the `FailedScheduling` message carefully — it says
   "insufficient IP addresses," not "insufficient cpu." The CPU (77%)
   and memory (57%) utilization confirm resources are available; the
   issue is IP allocation.

2. **Traced to the subnet, not the node.** A generic assistant might
   say "add more nodes." The skill recognises that adding nodes to the
   same exhausted subnets makes the problem worse — each new node's
   warm ENI pool consumes more IPs from an already-depleted subnet.

3. **Ruled out kubelet and taint issues with positive evidence.** All
   nodes are `Ready` with no conditions or taints. The skill uses this
   passing probe to eliminate KUBELET_ERROR, NODE_PRESSURE, and
   TAINT_SCHEDULING — narrowing to VPC_CNI_IP_EXHAUSTION.

4. **Recommended prefix delegation, not just bigger subnets.** The
   primary remediation is enabling prefix delegation (`ENABLE_PREFIX_
   DELEGATION=true`), which multiplies the IP capacity per node from
   29 to ~144 pods. Creating wider subnets is the secondary fix.
   A generic assistant would only suggest bigger subnets.

## Slash-command invocation

```
/aws:troubleshoot-eks-nodegroup
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why pods are stuck Pending with insufficient IPs"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: eks-nodegroup-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-cluster follow-up (optional, requires kubectl + AWS CLI)

After remediating, validate pod scheduling:

```bash
# Confirm prefix delegation is enabled
kubectl get ds aws-node -n kube-system -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ENABLE_PREFIX_DELEGATION")].value}'

# Confirm pods are now Running
kubectl get pods -A --field-selector status.phase=Pending
# Should return empty if all pods scheduled

# Check node IP allocation after CNI restart
kubectl describe node <node> | grep -A10 "Allocated resources"
```

Then monitor pod scheduling over 10-15 minutes to confirm all Pending
pods transition to Running.
