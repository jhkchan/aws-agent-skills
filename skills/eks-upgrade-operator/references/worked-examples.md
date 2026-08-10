# EKS Upgrade Worked Examples

Load this reference for full worked examples of each verdict shape.
The blocks below show the exact PRE_CHECKS, STEPS with CONFIRM gate
(including ROLLBACK ADVISORY), and POST_VERIFY for each archetype.
Copy the shape that matches the target cluster's situation.

## READY — upgrade-control-plane (1.28 -> 1.29)

```text
OPERATION: upgrade-control-plane
VERDICT: READY
TARGET: prod-cluster-01 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] cluster status: ACTIVE
  - [PASS] no other update in progress
  - [PASS] target version 1.29 available in us-east-1
  - [PASS] target is exactly N+1 from current (1.28)
  - [PASS] VPC-CNI v1.16.0 compatible with both 1.28 and 1.29
  - [PASS] CoreDNS v1.11.1-eksbuild.4 compatible with both 1.28 and 1.29
  - [PASS] kube-proxy v1.28.7-minimal-1 compatible with both 1.28 and 1.29
    (will upgrade to v1.29.x after control plane)
  - [PASS] kubent scan clean for 1.29 (no FlowSchema v1beta1 in use)
  - [PASS] all managed node groups at 1.28 (will upgrade after control plane)
  - [PASS] all nodes Ready
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
  4. After control plane is 1.29, upgrade add-ons to 1.29-compatible:
     aws eks update-addon --cluster-name prod-cluster-01 \
       --addon-name kube-proxy --addon-version v1.29.3-minimal-1 \
       --resolve-conflicts OVERWRITE
     aws eks update-addon --cluster-name prod-cluster-01 \
       --addon-name coredns --addon-version v1.11.1-eksbuild.6 \
       --resolve-conflicts OVERWRITE
POST_VERIFY:
  - (pending execution)
  - aws eks describe-cluster --name prod-cluster-01 → version 1.29
  - kubectl get nodes -o wide → all nodes Ready, still on 1.28
    (node group upgrade is the next operation)
  - kubectl get pods -n kube-system → no CrashLoopBackOff
  - kubectl get apiservices | grep False → none
ROLLBACK: control plane CANNOT be rolled back (etcd migration is one-way)
NOTES:
  - Node groups are still on 1.28 — they are incompatible with the new
    control plane. Run upgrade-nodegroup for each managed node group
    immediately after this operation completes.
  - Fargate pods will restart automatically to align kubelet with 1.29.
    Plan for a brief restart window for Fargate workloads.
  - The API server will reject mutations for 5-15 minutes during the
    etcd migration. Do not run kubectl apply during this window.
  - If the upgrade fails partway, AWS auto-retries transient failures.
    Persistent failures require AWS support — the cluster may be in
    UPDATING or FAILED state.
```

## READY — upgrade-nodegroup (rolling update with surge)

```text
OPERATION: upgrade-nodegroup
VERDICT: READY
TARGET: prod-cluster-01 / nodegroup: prod-ng-1 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] node group status: ACTIVE
  - [PASS] cluster control plane at 1.29 (target matches)
  - [PASS] target node version 1.29 <= cluster version 1.29
  - [PASS] PDB check: 2 PDBs found, both allow >= 1 disruption
  - [PASS] subnet spare IPs: 47 available (>= maxSurge+1)
  - [PASS] EC2 instance quota: 20 m5.large in use, 30 quota
    (10 spare, covers maxSurge: 2)
  - [PASS] updateConfig: maxUnavailable: 1, maxSurge: 2
STEPS:
  1. CONFIRM: About to update-nodegroup-version on prod-cluster-01 /
     prod-ng-1 from 1.28 to 1.29 in account 111111111111 region
     us-east-1. Strategy: surge (maxUnavailable: 1, maxSurge: 2). EKS
     will create 2 new nodes on 1.29, then drain 1.28 nodes one at a
     time. PDBs will be respected. Estimated duration: 20-30 minutes
     (5 nodes, ~5 minutes per drain). ROLLBACK ADVISORY: node group
     CAN be rolled back to 1.28 if the previous AMI is available.
     Proceed? (yes/no)
  2. aws eks update-nodegroup-version \
       --cluster-name prod-cluster-01 \
       --nodegroup-name prod-ng-1 \
       --kubernetes-version 1.29 \
       --release-version 1.29.3-20240807 \
       --region us-east-1
  3. Poll until Successful:
     aws eks describe-update --name prod-cluster-01 \
       --update-id <update-id>
  4. Watch node replacement:
     kubectl get nodes -w
POST_VERIFY:
  - (pending execution)
  - aws eks describe-nodegroup --cluster-name prod-cluster-01 \
      --nodegroup-name prod-ng-1 → version 1.29, status ACTIVE
  - kubectl get nodes -l eks.amazonaws.com/nodegroup=prod-ng-1 → all
    Ready, all at 1.29
  - kubectl get pods --all-namespaces --field-selector \
      spec.nodeName=<any-upgraded-node> → no CrashLoopBackOff
ROLLBACK: node group CAN be rolled back to 1.28 if the 1.28 AMI is
          still in the EKS AMI repository
NOTES:
  - The surge strategy (maxSurge: 2) creates 2 new nodes before draining,
    so workload capacity is never below the original count. This requires
    spare subnet IPs and instance quota.
  - If a PDB blocks drain on a node, the upgrade halts on that node.
    Patch the PDB to allow at least 1 disruption, then resume.
  - DaemonSets (VPC-CNI, kube-proxy, node-exporter) are not evicted
    during drain (--ignore-daemonsets). They will restart on the new
    nodes automatically.
```

## BLOCKED — PDB blocks drain

```text
OPERATION: upgrade-nodegroup
VERDICT: BLOCKED
TARGET: prod-cluster-01 / nodegroup: prod-ng-1 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] node group status: ACTIVE
  - [PASS] cluster control plane at 1.29
  - [PASS] target node version 1.29 <= cluster version 1.29
  - [FAIL] PDB "payments-api-pdb" in namespace payments has
    minAvailable: 4 and only 4 replicas exist. allowedDisruptions: 0.
    Drain cannot evict any pod. The upgrade would halt on every node
    running a payments-api pod.
  - [PASS] subnet spare IPs: 47 available
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ROLLBACK: (none)
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
