# End-to-end usage scenario: eks-upgrade-operator

A walkthrough showing the skill planning a full EKS cluster upgrade from
1.28 to 1.29 with managed node groups and EKS add-ons. The pre-checks
pass on add-on bridge versions, deprecated API scan, PDBs, and node
group versions, producing a READY plan with the exact CLI sequence and
the CONFIRM gate noting control plane CANNOT be rolled back. Contrasted
with the BLOCKED case where a PDB blocks node drain.

## Input (user prompt)

> We need to upgrade prod-cluster-01 from 1.28 to 1.29. It has 2
> managed node groups (prod-ng-1, prod-ng-2), each with 5 nodes. EKS
> add-ons are VPC-CNI, CoreDNS, kube-proxy. Standard rolling update.

```json
{
  "Operation": "upgrade-control-plane",
  "Cluster": "prod-cluster-01",
  "CurrentVersion": "1.28",
  "TargetVersion": "1.29",
  "Region": "us-east-1",
  "ClusterMetadata": {
    "status": "ACTIVE",
    "version": "1.28",
    "logging": {"clusterLogging": [
      {"types": ["api","audit","authenticator","controllerManager","scheduler"], "enabled": true}
    ]}
  },
  "InProgressUpdates": "none",
  "EksAddons": [
    {"name": "vpc-cni", "version": "v1.17.3-eksbuild.2", "status": "ACTIVE",
     "compatWith_1_28": true, "compatWith_1_29": true},
    {"name": "coredns", "version": "v1.11.1-eksbuild.4", "status": "ACTIVE",
     "compatWith_1_28": true, "compatWith_1_29": true},
    {"name": "kube-proxy", "version": "v1.28.7-minimal-1", "status": "ACTIVE",
     "compatWith_1_28": true, "compatWith_1_29": true}
  ],
  "ManagedNodeGroups": [
    {"name": "prod-ng-1", "version": "1.28", "status": "ACTIVE"},
    {"name": "prod-ng-2", "version": "1.28", "status": "ACTIVE"}
  ],
  "NodeVersions": "all 10 nodes Ready at v1.28.x",
  "KubentScan_1_29": "clean — no deprecated APIs in use",
  "PodDisruptionBudgets": "all PDBs have allowedDisruptions >= 1"
}
```

## Skill output

```text
OPERATION: upgrade-control-plane
VERDICT: READY
TARGET: prod-cluster-01 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] cluster status: ACTIVE
  - [PASS] no other update in progress
  - [PASS] target version 1.29 available in us-east-1
  - [PASS] target is exactly N+1 from current (1.28)
  - [PASS] VPC-CNI v1.17.3-eksbuild.2 compatible with both 1.28 and 1.29
    (bridge version)
  - [PASS] CoreDNS v1.11.1-eksbuild.4 compatible with both 1.28 and 1.29
    (bridge version)
  - [PASS] kube-proxy v1.28.7-minimal-1 compatible with both 1.28 and
    1.29 (bridge version; will upgrade to v1.29.x after control plane)
  - [PASS] kubent scan clean for 1.29 (no FlowSchema v1beta1 in use)
  - [PASS] all managed node groups at 1.28 (will upgrade after control plane)
  - [PASS] all nodes Ready (10 nodes, all v1.28.x)
  - [PASS] all PDBs allow at least 1 disruption
STEPS:
  1. CONFIRM: About to update-cluster-version on prod-cluster-01
     from 1.28 to 1.29 in account 111111111111 region us-east-1.
     This will cause a 5-15 minute API mutation window (API reads
     continue, applications keep running). ROLLBACK ADVISORY: EKS
     control plane upgrades CANNOT be rolled back. Estimated total
     duration: 15-30 minutes. Proceed? (yes/no)
  2. aws eks update-cluster-version \
       --name prod-cluster-01 \
       --kubernetes-version 1.29 \
       --region us-east-1
  3. Poll until Successful:
     aws eks describe-update --name prod-cluster-01 \
       --update-id <update-id-from-step-2>
  4. After control plane is 1.29, upgrade add-ons to latest 1.29-compatible:
     aws eks update-addon --cluster-name prod-cluster-01 \
       --addon-name kube-proxy --addon-version v1.29.3-minimal-1 \
       --resolve-conflicts PRESERVE
     aws eks update-addon --cluster-name prod-cluster-01 \
       --addon-name coredns --addon-version v1.11.3-eksbuild.3 \
       --resolve-conflicts PRESERVE
     aws eks update-addon --cluster-name prod-cluster-01 \
       --addon-name vpc-cni --addon-version v1.18.4-eksbuild.1 \
       --resolve-conflicts PRESERVE
  5. Then upgrade each managed node group:
     aws eks update-nodegroup-version --cluster-name prod-cluster-01 \
       --nodegroup-name prod-ng-1 --kubernetes-version 1.29 \
       --release-version 1.29.3-20260807
     aws eks update-nodegroup-version --cluster-name prod-cluster-01 \
       --nodegroup-name prod-ng-2 --kubernetes-version 1.29 \
       --release-version 1.29.3-20260807
POST_VERIFY:
  - (pending execution)
  - aws eks describe-cluster --name prod-cluster-01 → version 1.29
  - kubectl get nodes -o wide → all nodes Ready, at v1.29.x
  - kubectl get pods -n kube-system → no CrashLoopBackOff
  - kubectl get apiservices | grep False → none
  - aws eks describe-addon --cluster-name prod-cluster-01 --addon-name
    vpc-cni → version v1.18.4-eksbuild.1, status ACTIVE
  - kubectl rollout status deployment/canary -n canary → successfully
    rolled out
ROLLBACK: control plane CANNOT be rolled back (etcd migration is one-way).
          Node groups CAN be rolled back to 1.28 if AMI is still available.
NOTES:
  - The API server will reject mutations for 5-15 minutes during the
    etcd migration. Do not run kubectl apply during this window.
  - Node groups are still on 1.28 after the control plane upgrade —
    they are incompatible until upgraded. Run upgrade-nodegroup for
    each immediately after.
  - DaemonSets (VPC-CNI, kube-proxy) are not evicted during node group
    drain (--ignore-daemonsets). They will restart on new nodes.
  - If a PDB blocks drain on a node, the upgrade halts on that node.
    Patch the PDB to allow >= 1 disruption, then resume.
```

## Contrast — BLOCKED case (PDB blocks drain)

If the operator had a `payments-api` deployment with
`PodDisruptionBudget minAvailable: 4` and replicas=4, the node group
upgrade pre-check would fire:

```text
OPERATION: upgrade-nodegroup
VERDICT: BLOCKED
TARGET: prod-cluster-01 / prod-ng-1 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] node group status: ACTIVE
  - [PASS] cluster control plane at 1.29
  - [PASS] target node version 1.29 <= cluster version 1.29
  - [FAIL] PodDisruptionBudget "payments-api-pdb" in namespace payments
    has minAvailable: 4 and only 4 replicas exist.
    allowedDisruptions: 0. Drain cannot evict any payments-api pod.
    The node group upgrade would halt on every node running a
    payments-api pod.
  - [PASS] subnet spare IPs: 47 in subnet-aaa, 51 in subnet-bbb
  - [PASS] EC2 instance quota covers maxSurge
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ROLLBACK: (none — pre-checks failed)
NOTES:
  - Patch the PDB to allow at least 1 disruption before retrying:
    kubectl patch pdb payments-api-pdb -n payments --type=json \
      -p='[{"op":"replace","path":"/spec/minAvailable","value":3}]'
    Then verify: kubectl get pdb payments-api-pdb -n payments \
      -o jsonpath='{.status.disruptionsAllowed}'
    DisruptionsAllowed should be >= 1.
  - Alternatively, scale the deployment to 5 replicas so minAvailable: 4
    still allows 1 disruption:
    kubectl scale deployment payments-api -n payments --replicas=5
  - After the upgrade, restore the PDB to its original value.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant emits
   the update-cluster-version command directly. The skill runs 10
   deterministic pre-checks and BLOCKS before triggering a control plane
   upgrade that has incompatible add-ons or removed APIs in use.

2. **One-way operation advisory.** A generic assistant omits that control
   plane upgrades cannot be rolled back. The skill surfaces this in the
   CONFIRM gate so the operator knows the pre-checks are the safety net.

3. **Add-on bridge-version check.** A generic assistant omits that EKS
   requires add-ons compatible with BOTH versions BEFORE the control
   plane upgrade. The skill surfaces the bridge version requirement and
   blocks if the current add-on is incompatible.

4. **Deprecated API scan (kubent).** A generic assistant omits the
   deprecated API scan. The skill surfaces `kubent --target-version 1.29`
   as a pre-check; workloads using removed APIs (e.g., FlowSchema
   v1beta1) will fail to apply post-upgrade.

5. **PDB pre-check for node group upgrade.** A generic assistant omits
   the PDB check. The skill pre-checks every PDB and computes
   `disruptionsAllowed` per node — surfacing the patch command before
   the upgrade halts mid-flight.

6. **Surge capacity check.** A generic assistant omits subnet IP and
   instance quota checks for surge upgrades. The skill verifies spare
   capacity before authorizing `maxSurge > 0`.

7. **Sequence enforcement.** A generic assistant lets the operator
   upgrade node groups before the control plane. The skill BLOCKS —
   node group versions must be <= the control plane version.

8. **Sequential minor-version requirement.** A generic assistant lets
   the operator attempt 1.27 -> 1.29 directly. The skill BLOCKS and
   targets 1.28 first.

## Slash-command invocation

```
/aws:operate-eks-upgrade
```

Or via the orchestrator:

```
/aws:pipeline
You: "upgrade prod-cluster-01 from 1.28 to 1.29"
```

The orchestrator emits
`[Phase: Operate | Skills routed: eks-upgrade-operator]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "upgrade EKS cluster prod-cluster-01 to 1.29"
# [Phase: Operate | Skills routed: eks-upgrade-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the control plane and node groups are upgraded:

```bash
# Verify all nodes are at the new version
kubectl get nodes -o wide --profile default

# Verify all EKS add-ons are at 1.29-compatible versions and ACTIVE
for addon in vpc-cni coredns kube-proxy; do
  aws eks describe-addon --cluster-name prod-cluster-01 \
    --addon-name $addon --profile default \
    --query '{Name:addon.addonName,Version:addon.addonVersion,Status:addon.status}'
done

# Verify no API services are unavailable
kubectl get apiservices | grep False

# Verify no pods in CrashLoopBackOff
kubectl get pods --all-namespaces --field-selector status.phase=Failed

# Run kubent to confirm no deprecated APIs remain
kubent --target-version 1.29

# Sample application metrics for the 15-minute post-upgrade window
aws cloudwatch get-metric-statistics \
  --namespace Application \
  --metric-name ErrorRate \
  --dimensions Name=Cluster,Value=prod-cluster-01 \
  --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average \
  --profile default
```
