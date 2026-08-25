# Advanced Patterns (load on demand) — DynamoDB Auto-Scaling Deployer

The configuration dependency graph and 2023-2026 feature changes, moved verbatim from SKILL.md.


---

## Configuration dependency graph (novel heuristic) (moved from SKILL.md)


DynamoDB auto-scaling configurations are NOT independent. Several
depend on the table being in PROVISIONED mode; several are
immutable or destructive if changed; several silently break when
the table switches modes. Use this graph to sequence provisioning
and to debug "why is my GSI throttling when my table is fine?"

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Table capacity mode | Table must exist | Switching provisioned→on-demand DETACHES all scaling policies; switching back requires re-registration | determines if auto-scaling is applicable |
| Scalable target (table) | Table in PROVISIONED mode; `RegisterScalableTarget` for dimension `table:<table-name>` | `MinCapacity` and `MaxCapacity` define the scaling envelope; outside this range, no scaling occurs | target tracking policy attachment |
| Scalable target (GSI) | GSI exists; table in PROVISIONED mode; `RegisterScalableTarget` for dimension `table:<table-name>` with `resourceId=table/<table-name>/index/<gsi-name>` | GSI capacity CANNOT be set separately from table mode — inherits PROVISIONED from parent table | GSI target tracking policy |
| Target tracking policy | Scalable target registered; CloudWatch metric available (`DynamoDBReadCapacityUtilization` / `DynamoDBWriteCapacityUtilization`) | target value (utilization %) + scale-in cooldown + scale-out cooldown set at policy creation | automatic capacity adjustment |
| Application auto-scaling role | IAM role with trust to `application-autoscaling.amazonaws.com` (service-linked role `AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback` auto-created) | missing role → `AccessDenied` on RegisterScalableTarget | CloudFormation/CLI scaling operations |
| Min/Max capacity | Min ≤ current provisioned ≤ Max at registration time | MinCapacity > MaxCapacity → ValidationError; MaxCapacity > account-level limit → LimitExceededException | scaling envelope bounds |
| On-demand mode | Table exists; `BillingMode=PAY_PER_REQUEST` | ALL scaling policies detached; `BillingModeSummary` reflects on-demand | no scaling policy needed |
| Throttle monitoring | CloudWatch `AWS/DynamoDB` namespace | `ConsumedReadCapacityUnits` vs `ProvisionedReadCapacityUnits` gap signals under-provisioning | alerting and remediation |

**The mode-switch row is the one a baseline model misses.** Switching
a table from PROVISIONED to on-demand SILENTLY DETACHES all scaling
policies. Switching back to PROVISIONED does NOT re-attach them —
you must re-register scalable targets and re-create policies. The
procedure below forces an explicit capacity mode decision before any
scaling configuration.

**Cross-dependency gotchas:**
- A GSI inherits its capacity mode from the parent table. A
  PROVISIONED table can have auto-scaled GSIs; an on-demand table's
  GSIs are also on-demand (no scaling policies).
- `MinCapacity` must be ≤ the table's currently provisioned RCU/WCU
  at the time of registration. If you lower provisioned throughput
  below Min, scaling will immediately raise it back.
- Target tracking uses the DynamoDB-managed CloudWatch metric
  `DynamoDBReadCapacityUtilization` / `DynamoDBWriteCapacityUtilization`
  — NOT `ConsumedReadCapacityUnits`. These are pre-computed
  utilization metrics that account-auto-scaling owns.
- Scale-in cooldown (default 0s for DynamoDB) determines how fast
  capacity is reduced. A longer cooldown prevents flapping but
  delays cost reduction.

## Step 7 — Recent features (2023-2026) (moved from SKILL.md)


**Recent AWS features (2023-2026):**

- **On-demand vs provisioned capacity mode auto-switching
  (2024-2025):** DynamoDB can now automatically switch between
  on-demand and provisioned capacity modes based on usage
  patterns. This feature analyzes 24-hour usage windows and
  recommends or applies the cost-optimal mode. Requires opt-in
  via `aws dynamodb update-table --billing-mode
  PROVISIONED_AND_ON_DEMAND_AUTO_SWITCH` (where available). Useful
  for workloads with diurnal traffic patterns.

- **GSI auto-scaling MaxCapacity increase (2023-2024):** GSI
  MaxCapacity limits were raised to match table limits (up to
  40,000 RCU/WCU for most regions). Previously GSIs had lower
  limits than tables.

- **Faster scale-out for DynamoDB (2023-2024):** Application Auto
  Scaling reduced the evaluation interval for DynamoDB from 60s
  to as low as 15s for certain metrics, enabling faster response
  to traffic bursts.

- **Predictive scaling for DynamoDB (2024-2025):** Application
  Auto Scaling now supports predictive scaling policies for
  DynamoDB, using historical traffic patterns to pre-scale
  capacity before predicted bursts. Complements (does not
  replace) target tracking.

- **Capacity advisor (2023-2025):** DynamoDB capacity advisor
  analyzes usage and recommends optimal capacity mode (on-demand
  vs provisioned) and scaling parameters. Accessible via the
  console and `aws dynamodb describe-capacity-reservations`.

- **CloudWatch metric `DynamoDBReadCapacityUtilization` /
  `DynamoDBWriteCapacityUtilization` (2023-2024):** These pre-
  computed utilization metrics (consumed/provisioned ratio) are
  now first-class CloudWatch metrics, not just internal to
  Application Auto Scaling. Useful for custom dashboards and
  alarms independent of scaling policies.