# EKS Upgrade Procedures Reference

Load this reference when planning or executing any EKS upgrade operation.
The procedures below are the canonical sequences for each upgrade
archetype, with pre-checks, command sequence, post-verification, and
rollback notes.

## Decision tree — which upgrade archetype

| Scenario | Use | Why |
|---|---|---|
| Cluster on N-3 or older | **Sequential minor upgrades** | EKS requires sequential; target N+1 first |
| Add-ons incompatible with target Kubernetes | **Pre-upgrade add-on upgrade** | Required before control plane |
| Control plane on current; node groups behind | **Node group upgrade** | Align kubelet to control plane |
| Node group upgrade with capacity headroom | **Surge upgrade (maxSurge > 0)** | Faster, no workload downtime |
| Node group upgrade without capacity | **Rolling upgrade (maxUnavailable: 1)** | Slower, but no spare IPs needed |
| Self-managed nodes (kops, EC2 ASG) | **Manual drain and replace** | EKS API does not manage these nodes |
| Fargate profile | **Auto-restart on control plane upgrade** | No node drain needed |
| EKS Auto Mode | **Control plane only** | Auto Mode handles node lifecycle |
| EKS hybrid nodes | **Manual on-prem upgrade** | EKS API does not manage hybrid nodes |
| Cluster past standard support | **Force-upgrade incoming** | AWS auto-upgrades after extended support |
| Failed control plane upgrade | **AWS support escalation** | No customer rollback path |
| Failed node group upgrade | **Roll back node group** | Previous AMI is in the EKS AMI repo |

## End-to-end upgrade sequence (canonical)

For a cluster on 1.28 upgrading to 1.29 with managed node groups and EKS
add-ons:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Pre-upgrade add-on upgrade (to a "bridge" version         │
│    compatible with BOTH 1.28 and 1.29)                      │
│    aws eks update-addon --addon-name vpc-cni ...            │
│    aws eks update-addon --addon-name coredns ...            │
│    aws eks update-addon --addon-name kube-proxy ...         │
├─────────────────────────────────────────────────────────────┤
│ 2. Deprecated API scan                                      │
│    kubent --kubernetes-version 1.29                         │
│    Fix all flagged resources before proceeding              │
├─────────────────────────────────────────────────────────────┤
│ 3. PDB check                                                │
│    kubectl get poddisruptionbudgets --all-namespaces        │
│    Patch any PDB with disruptionsAllowed: 0                 │
├─────────────────────────────────────────────────────────────┤
│ 4. Control plane upgrade (ONE-WAY)                          │
│    aws eks update-cluster-version --kubernetes-version 1.29 │
│    aws eks describe-update --update-id <id> (poll)          │
├─────────────────────────────────────────────────────────────┤
│ 5. Post-control-plane add-on upgrade (to latest 1.29)       │
│    aws eks update-addon --addon-name vpc-cni ...            │
│    aws eks update-addon --addon-name coredns ...            │
│    aws eks update-addon --addon-name kube-proxy ...         │
├─────────────────────────────────────────────────────────────┤
│ 6. Managed node group upgrade (per node group)              │
│    aws eks update-nodegroup-version                         │
│      --kubernetes-version 1.29 --release-version <ami>      │
│    aws eks describe-update --update-id <id> (poll)          │
├─────────────────────────────────────────────────────────────┤
│ 7. Self-managed node drain and replace (per node)           │
│    kubectl cordon <node>                                    │
│    kubectl drain <node> --ignore-daemonsets                 │
│      --delete-emptydir-data                                │
│    (terminate / rebuild the node)                           │
├─────────────────────────────────────────────────────────────┤
│ 8. Post-upgrade verification                                │
│    kubectl get nodes -o wide                                │
│    kubectl get pods -A --field-selector status.phase=Failed │
│    kubectl get apiservices | grep False                     │
└─────────────────────────────────────────────────────────────┘
```

## Procedure: Pre-upgrade add-on upgrade

**When to use:** BEFORE the control plane upgrade. Bring each add-on to
a version compatible with both current and target Kubernetes.

**Pre-checks:**
1. Add-on `status: ACTIVE` (not `DEGRADED`).
2. Target add-on version is in `describe-addon-versions
   --kubernetes-version <both current and target>` output.
3. ConfigurationValues backed up (kubectl get deployment/daemonset).

**Command sequence:**
```bash
# 1. Find the bridge version for VPC-CNI
aws eks describe-addon-versions \
  --kubernetes-version 1.29 \
  --addon-name vpc-cni \
  --query 'addons[].addonVersions[].{Version:addonVersion,Compat:compatibilities[0].clusterVersion}' \
  --output table

# 2. Back up current state
kubectl get daemonset aws-node -n kube-system -o yaml > /tmp/vpc-cni-preupgrade.yaml

# 3. Upgrade (OVERWRITE discards local edits; PRESERVE keeps them)
aws eks update-addon \
  --cluster-name <cluster> \
  --addon-name vpc-cni \
  --addon-version v1.16.0-eksbuild.1 \
  --resolve-conflicts PRESERVE \
  --region <region>

# 4. Wait for the update to complete
aws eks describe-update --name <cluster> --update-id <id>

# 5. Verify the daemonset is healthy
kubectl get pods -n kube-system -l k8s-app=aws-node
```

**Common failure modes:**
- `InvalidParameterException` — add-on version not compatible with
  current Kubernetes. Choose a different bridge version.
- `ConflictException` — ConfigurationValues conflicts with local edits.
  Use `--resolve-conflicts OVERWRITE` after backing up.

## Procedure: Deprecated API scan

**When to use:** BEFORE the control plane upgrade. Detect workloads
using APIs removed in the target version.

**Command sequence (kubent):**
```bash
# Install kubent if not present
# https://github.com/doitintl/kube-deprecation

# Run against the cluster
kubent

# Or, for a specific target version
kubent --output-text --target-version 1.29
```

**Command sequence (kubectl convert):**
```bash
# Convert a manifest to the new API version
kubectl convert --output-version networking.k8s.io/v1 -f ingress.yaml | kubectl apply -f -

# Find resources using deprecated APIs
kubectl get ingresses --all-namespaces -o json | \
  jq -r '.items[] | select(.apiVersion | startswith("extensions/v1beta1") or startswith("networking.k8s.io/v1beta1")) | "\(.metadata.namespace)/\(.metadata.name) \(.apiVersion)"'

kubectl get cronjobs --all-namespaces -o json | \
  jq -r '.items[] | select(.apiVersion == "batch/v1beta1") | "\(.metadata.namespace)/\(.metadata.name)"'
```

**Common findings and fixes:**

| Deprecated API | Fix |
|---|---|
| `extensions/v1beta1 Ingress` | Convert to `networking.k8s.io/v1 Ingress`; update `pathType: Prefix` (required in v1); update `backend` structure |
| `networking.k8s.io/v1beta1 Ingress` | Same as above |
| `batch/v1beta1 CronJob` | Convert to `batch/v1 CronJob` (no schema change) |
| `policy/v1beta1 PodSecurityPolicy` | Migrate to Pod Security Admission (PSA); set `podSecurity` admission on namespaces |
| `autoscaling/v2beta1 HorizontalPodAutoscaler` | Convert to `autoscaling/v2 HorizontalPodAutoscaler` (schema change for metrics) |
| `autoscaling/v2beta2 HorizontalPodAutoscaler` | Same as above |

## Procedure: Control plane upgrade

**When to use:** Move the control plane to the next minor Kubernetes
version. ONE-WAY — no rollback.

**Pre-checks:**
1. Cluster `status: ACTIVE`.
2. No update in progress.
3. Target version is N+1 from current.
4. All add-ons at bridge versions (compatible with both).
5. kubent scan clean.
6. All managed node groups at current cluster version.
7. All nodes Ready.
8. Control-plane logging enabled (audit, api, authenticator).

**Command sequence:**
```bash
# 1. Capture pre-state
aws eks describe-cluster --name <cluster> --output json > /tmp/<cluster>-pre-$(date +%s).json
kubectl get nodes -o wide > /tmp/nodes-pre-$(date +%s).txt
kubectl get pods --all-namespaces -o wide > /tmp/pods-pre-$(date +%s).txt

# 2. Execute (ONE-WAY)
aws eks update-cluster-version \
  --name <cluster> \
  --kubernetes-version <target> \
  --region <region>

# Capture the updateId from the response
# 3. Poll until Successful
aws eks describe-update --name <cluster> --update-id <update-id>

# 4. After Successful, upgrade add-ons to latest target version
aws eks update-addon --cluster-name <cluster> \
  --addon-name kube-proxy --addon-version <latest-1.29-version> \
  --resolve-conflicts PRESERVE
```

**Post-verification:**
- `describe-cluster` shows `version: <target>`.
- `kubectl get nodes -o wide` — all nodes Ready (still on old version;
  node group upgrade is next).
- `kubectl get apiservices | grep False` — no unavailable API services.
- `kubectl get pods -n kube-system` — no CrashLoopBackOff.

**Rollback:** NONE. Control plane upgrades are one-way. If the upgrade
fails partway, AWS auto-retries transient failures. Persistent failures
require AWS support.

## Procedure: Managed node group upgrade (rolling)

**When to use:** Align managed node group kubelet to the new control
plane version. Default strategy: one node at a time.

**Pre-checks:**
1. Node group `status: ACTIVE`.
2. Cluster control plane at the target version.
3. PDB check: `kubectl get poddisruptionbudgets --all-namespaces` —
   `disruptionsAllowed >= 1` for each PDB that has pods on this node
   group.
4. Subnet IPs available >= `maxUnavailable + maxSurge`.
5. EC2 instance quota covers surge.

**Command sequence:**
```bash
# 1. Find the release version for the target Kubernetes
aws ssm get-parameter \
  --name /aws/service/eks/optimized-ami/<kubernetes-version>/amazon-linux-2023/x86_64/standard/recommended/image_id \
  --region <region>
# Or use the EKS API
aws eks describe-addon-versions --kubernetes-version <target> \
  --query 'addons[].addonVersions[].compatibilities[]'

# 2. Execute
aws eks update-nodegroup-version \
  --cluster-name <cluster> \
  --nodegroup-name <nodegroup> \
  --kubernetes-version <target> \
  --release-version <release-version> \
  --region <region>

# 3. Poll until Successful
aws eks describe-update --name <cluster> --nodegroup-name <nodegroup> \
  --update-id <update-id>

# 4. Watch node replacement
kubectl get nodes -l eks.amazonaws.com/nodegroup=<nodegroup> -w
```

**Common failure modes:**
- PDB blocks drain — node stuck in `NotReady`. Patch the PDB to allow
  >= 1 disruption, then resume.
- Subnet IP exhaustion — surge node fails to launch. Free IPs or use a
  different subnet.
- AMI not found — the release version does not exist. Use
  `aws eks describe-addon-versions` to list valid versions.

## Procedure: Managed node group upgrade (force with surge)

**When to use:** Faster node group upgrade when capacity allows.

**updateConfig parameters:**
- `maxUnavailable: 1` — drain one node at a time (default).
- `maxUnavailable: 2` — drain two nodes at a time.
- `maxSurge: 1` — create one new node before draining any old one.
- `maxSurge: 2` — create two new nodes before draining.

**Set the updateConfig before calling update-nodegroup-version:**
```bash
aws eks update-nodegroup-config \
  --cluster-name <cluster> \
  --nodegroup-name <nodegroup> \
  --update-config maxUnavailable=1,maxSurge=2

# Then proceed with update-nodegroup-version
```

**Cost:** Surge nodes bill while they exist. A 5-node group with
`maxSurge: 2` briefly has 7 nodes (~5-10 minutes during upgrade).

## Procedure: Self-managed node drain and replace

**When to use:** Nodes not in an EKS managed node group (kops, EC2 ASG,
or standalone EC2 with user-data kubelet bootstrap).

**Command sequence:**
```bash
# 1. Cordon the node (mark unschedulable)
kubectl cordon <node-name>

# 2. Drain the node (evict pods)
kubectl drain <node-name> \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --timeout=5m \
  --grace-period=30

# 3. Verify all non-DaemonSet pods are gone
kubectl get pods --all-namespaces --field-selector spec.nodeName=<node-name>

# 4. Terminate the EC2 instance (if ASG-managed, the ASG replaces it)
aws ec2 terminate-instances --instance-ids <instance-id>

# Or, for kops: kops rolling-update cluster --instance-group <ig-name>
# Or, for a standalone node: rebuild with new AMI and re-join the cluster

# 5. Wait for the new node to join
kubectl get nodes -w

# 6. Repeat for each self-managed node
```

**Common failure modes:**
- PDB blocks drain — `error: unable to drain node due to
  PodDisruptionBudget`. Patch the PDB or scale up the deployment.
- Pod with `emptyDir` not evicted — add `--delete-emptydir-data` (or
  `--force` after operator confirmation).
- Stranded pod — `kubectl delete pod <pod> -n <ns> --force
  --grace-period=0` as last resort (data loss possible for the emptyDir).

## Procedure: Fargate profile upgrade

**When to use:** Fargate workloads auto-restart on control plane
upgrade. No node drain needed.

**Verification only:**
```bash
# After control plane upgrade, Fargate pods will restart
kubectl get pods -n <fargate-namespace> -o wide
# The node column shows new Fargate nodes with the new kubelet version

# Verify Fargate profile is intact
aws eks describe-fargate-profile --cluster-name <cluster> \
  --fargate-profile-name <profile>
```

## Procedure: EKS Auto Mode upgrade

**When to use:** Cluster with `computeConfig.enabled: true`.

**Operator actions:**
1. Pre-upgrade add-on upgrades (VPC-CNI, CoreDNS, kube-proxy) — same as
   standard clusters.
2. Control plane upgrade — `update-cluster-version`.
3. Post-control-plane add-on upgrades.
4. Auto Mode handles node lifecycle — DO NOT run
   `update-nodegroup-version`.

**Verification:**
```bash
# Auto Mode nodes drift-replace after the control plane reaches target
kubectl get nodes -o wide
# Watch for new nodes appearing with the target Kubernetes version

# Check Auto Mode compute status
aws eks describe-cluster --name <cluster> \
  --query 'cluster.computeConfig'
```

## Procedure: EKS hybrid node upgrade

**When to use:** Cluster with `remoteNetworkConfig` and on-prem nodes
attached.

**Operator actions:**
1. Pre-upgrade add-on upgrades — same as standard clusters.
2. Control plane upgrade — `update-cluster-version`.
3. For each hybrid node:
   - SSH to the on-prem node.
   - Upgrade kubelet and container runtime to match the target
     Kubernetes version.
   - Restart kubelet.
   - Verify `kubectl get nodes` shows the node `Ready` at the new
     version.
4. Do NOT run `update-nodegroup-version` — it does not apply to hybrid
   nodes.

## Post-upgrade verification (run after every upgrade step)

```bash
# 1. Cluster version
aws eks describe-cluster --name <cluster> \
  --query 'cluster.version'

# 2. All nodes Ready and at the target version
kubectl get nodes -o wide

# 3. No pods in CrashLoopBackOff, ImagePullBackOff, or Failed
kubectl get pods --all-namespaces \
  --field-selector status.phase=Failed

# 4. No unavailable API services
kubectl get apiservices | grep False

# 5. All EKS add-ons at target-compatible versions and ACTIVE
aws eks list-addons --cluster-name <cluster>
# For each addon:
aws eks describe-addon --cluster-name <cluster> --addon-name <name> \
  --query '{Version:addon.addonVersion,Status:addon.status}'

# 6. Canary deployment rollout
kubectl rollout status deployment/canary -n canary

# 7. Application metric dashboards (5-15 minute window)
# Verify error rate is flat in CloudWatch / Prometheus / Datadog
```

## Rollback procedures

### Control plane — NO ROLLBACK

Once `update-cluster-version` starts, it cannot be canceled. AWS auto-
retries transient failures. Persistent failures require AWS support
intervention.

If the cluster enters `FAILED` state:
1. Open an AWS support case immediately.
2. Capture `describe-cluster`, `describe-update`, and CloudTrail logs
   for the upgrade window.
3. Do NOT attempt to delete and recreate the cluster — this loses all
   cluster state.

### Managed node group — CAN roll back

```bash
# Roll back the node group to the previous version (if AMI available)
aws eks update-nodegroup-version \
  --cluster-name <cluster> \
  --nodegroup-name <nodegroup> \
  --kubernetes-version <previous> \
  --release-version <previous-ami>
```

Verify the previous AMI is in the EKS AMI repository:
```bash
aws ssm get-parameter \
  --name /aws/service/eks/optimized-ami/<previous-kubernetes-version>/amazon-linux-2023/x86_64/standard/recommended/image_id
```

### Add-on — CAN roll back

```bash
# Downgrade the add-on
aws eks update-addon \
  --cluster-name <cluster> \
  --addon-name <name> \
  --addon-version <previous-version> \
  --resolve-conflicts OVERWRITE
```

### PDB patch — REVERSIBLE

```bash
# Restore the PDB to its original value after the upgrade
kubectl patch pdb <name> -n <ns> --type=json \
  -p='[{"op":"replace","path":"/spec/minAvailable","value":<original>}]}'
```

## Upgrade time benchmarks (2026, us-east-1)

| Operation | Typical duration |
|---|---|
| Pre-upgrade add-on upgrade | 1-3 min per add-on |
| Deprecated API scan (kubent) | <1 min |
| Control plane upgrade | 15-30 min |
| Managed node group rolling (5 nodes) | 25-45 min (5 min/node) |
| Managed node group surge (maxSurge: 2, 5 nodes) | 15-25 min |
| Self-managed node drain (per node) | 5-10 min |
| Fargate pod restart (per pod) | 30-60 seconds |
| Post-control-plane add-on upgrade | 1-3 min per add-on |
| Post-upgrade verification | 5-10 min |

## Common upgrade pitfalls

- **Skipped pre-upgrade add-on upgrade.** VPC-CNI incompatible with new
  Kubernetes -> new pods cannot get IPs -> pod stuck in
  ContainerCreating. Always upgrade add-ons first.
- **PDB with `minAvailable: 100%`.** Blocks drain indefinitely. Patch
  to allow >= 1 disruption before upgrade.
- **`maxUnavailable: 100%` on a production node group.** Drains all
  nodes simultaneously. Verify `updateConfig` before upgrade.
- **Surge upgrade without spare subnet IPs.** Surge nodes fail to
  launch; upgrade stalls. Check `AvailableIpAddressCount` first.
- **Self-managed node drain without `--ignore-daemonsets`.** Drain
  hangs forever on DaemonSet pods.
- **Skipped kubent scan.** Workloads using removed APIs fail silently
  after upgrade — the API server rejects them on next reconcile.
- **Deployed during control plane mutation window.** API writes fail
  for 5-15 minutes. Pause CI/CD during the upgrade.
- **Forgotten Fargate pod restart.** Fargate pods restart on control
  plane upgrade — plan for the brief restart window.
- **Trusted Auto Mode to upgrade everything.** Auto Mode handles nodes,
  but NOT add-ons. The operator still runs addon upgrades and the
  control plane upgrade.
