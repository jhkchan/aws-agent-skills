# Advanced Patterns (load on demand) — EKS Autoscaling Automator

Expert-knowledge deep dives, edge cases, appendices, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious autoscaling behaviors (moved from SKILL.md)

- **Karpenter v1 replaced `AWSNodeTemplate` with `EC2NodeClass` and
  `Provisioner` with `NodePool`.** A v0.32 manifest will NOT work on v1+
  without migration.

- **Karpenter consolidation has two modes.** `WhenEmpty` (only delete
  nodes with zero pods) is conservative. `WhenEmptyOrUnderutilized`
  (delete underutilized nodes, reschedule pods) is aggressive but
  disruptive. Start with `WhenEmpty`, graduate to
  `WhenEmptyOrUnderutilized` with disruption budgets.

- **Cluster Autoscaler does NOT scale down nodes with pods that have
  PDBs blocking eviction, anti-affinity constraints, or local storage.**
  These nodes stay forever, inflating costs.

- **KEDA scalers are triggered, not polled.** KEDA activates HPA when
  the trigger threshold is met (Kafka lag, SQS depth). When the trigger
  drops to zero, KEDA scales the deployment to zero (HPA alone cannot).

- **Spot interruption notices arrive via IMDS.** Karpenter handles this
  natively via `interruptionQueue`. NTH (Node Termination Handler) also
  polls IMDS. Do NOT run both — they conflict.

- **Overprovisioning pause-pods must use a priority class BELOW real
  workloads.** If pause-pods have equal or higher priority, real pods
  cannot preempt them, and the headroom is wasted.

- **VPA `Auto` mode recreates pods to apply new requests.** This causes
  brief outages. Never use `Auto` on single-replica Deployments. Use
  `Initial` (sets on creation) or `Off` (recommendations only).

- **descheduler `PodLifeTime` evicts old pods.** Set
  `maxNoOfPodsToEvictPerNode` and run in `DryRun` first.

- **Managed node group `desiredSize` is overridden by CA.** If CA is
  running, it adjusts `desiredSize` within min/max range. Do NOT set it
  manually.


## Appendix A — Karpenter vs CA decision tree (moved from SKILL.md)

```
New cluster? → Karpenter (AWS-recommended) unless org needs CA stability
Existing CA? → Consolidation needed? → Yes: migrate to Karpenter
                                  → No: keep CA
EKS Auto Mode available (1.29+)? → Use Auto Mode (simplest)
```


## Appendix B — HPA behavior quick reference (moved from SKILL.md)

| Scenario | scaleUp | scaleDown | Stabilization |
|---|---|---|---|
| API (bursty) | Max(100%/15s, 4 pods/15s) | Min(10%/60s) | Down: 300s |
| Worker (queue) | Max(100%/15s) | Min(5%/60s) | Down: 600s |
| Batch | Max(2 pods/60s) | Min(1/120s) | Down: 600s |

**Rule:** scale UP fast (users waiting), scale DOWN slow (avoid thrash).


## Appendix C — Spot instance diversification (moved from SKILL.md)

| Workload | Families | Min size |
|---|---|---|
| General web | c5, m5, c6i, m6i | large (2 vCPU) |
| Memory-heavy | r5, r6i, x2iedn | large |
| Compute-heavy | c5, c6i, c7i | xlarge (4 vCPU) |
| GPU (ML) | g4dn, g5, g6 | xlarge |

Karpenter flexible selector (AMD64, cost-optimized):
```yaml
requirements:
  - {key: karpenter.k8s.aws/instance-category, operator: In, values: ["c", "m"]}
  - {key: karpenter.k8s.aws/instance-generation, operator: Gt, values: ["5"]}
  - {key: karpenter.k8s.aws/instance-cpu, operator: In, values: ["2", "4", "8", "16"]}
  - {key: karpenter.sh/capacity-type, operator: In, values: ["spot", "on-demand"]}
```


## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Karpenter v1 GA (2024):** Breaking API changes — `Provisioner` →
  `NodePool`, `AWSNodeTemplate` → `EC2NodeClass`.
- **Disruption budgets (2024):** `disruption.budgets` on NodePool caps
  simultaneous node disruption. Use `nodes: "20%"` + business-hours
  freeze.
- **EKS Auto Mode (2025):** AWS-managed Karpenter + node lifecycle.
  Simplest path for new clusters. Enable via `update-cluster-config`.
- **KEDA v2.15 (2024-2025):** CloudWatch trigger, improved SQS scaler,
  scale-to-zero stabilization.
- **HPA v2 behavior (stable):** Fine-grained scale-up/down control with
  stabilization windows and policy selection.
- **VPA in-place resize (2025, K8s 1.33+):** Alpha feature allowing VPA
  to adjust requests WITHOUT recreating pods. EKS support expected 1.33+.


## Expert heuristic: autoscaling blast radius (moved from SKILL.md)

> ALWAYS start with conservative settings (Karpenter `WhenEmpty`, HPA
> 300s stabilization, descheduler DryRun). Enable aggressive settings
> only after observing conservative behavior for 1 week in production.

**Why:** autoscaling components interact: Karpenter consolidation feeds
pods to the scheduler, which respects priority + topology spread, which
affects HPA decisions, which affect KEDA triggers. A change in ANY
component can cascade.

**Wave-enabling pattern:**

| Phase | Karpenter | HPA | KEDA | Descheduler |
|---|---|---|---|---|
| 1 | `WhenEmpty` | CPU, 300s stab | Not installed | DryRun |
| 2 | `WhenEmpty` | + custom metrics | Installed (min 1) | DryRun |
| 3 | `WhenEmptyOrUnderutilized` + 20% budget | As 2 | As 2 | Enabled (3/node) |
| 4 | + spot + pause-pods | As 3 | Scale-to-zero | As 3 |

**Failure detection:** alarm on `karpenter_pods_state` Pending > 5 min
(capacity issue). Alarm on HPA `CurrentReplicas` oscillating > 50%
in 10 min (thrashing). Alarm on node count dropping > 20% in 5 min
(aggressive consolidation or mass spot eviction).
