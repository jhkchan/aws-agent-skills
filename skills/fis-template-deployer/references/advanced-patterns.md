# Advanced Patterns — FIS Template Deployer

Expert-knowledge deep dives, edge-case catalogs, and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Expert heuristic: tag-based target scoping is the safest mechanism (moved from SKILL.md)

A baseline model says "target all EC2 instances in the account." The
correct heuristic recognizes that FIS targets should be scoped to a
blast-radius-controlled set via resource tags.

```text
Target scoping mechanisms (safest to riskiest):
  ├── Resource tags (RECOMMENDED): match resources with specific tag key=value
  │     e.g., Filter: tag:FIS_Target = enabled AND tag:Environment = staging
  │     Pros: stable, auditable, explicit opt-in, version-controlled
  │     Cons: requires tagging discipline; untagged resources excluded
  ├── Resource IDs: specify exact resource IDs
  │     e.g., resourceIds: ["i-aaa111222", "i-bbb222333"]
  │     Pros: precise
  │     Cons: brittle — IDs change when instances are replaced (ASG, karpenter)
  ├── Filter patterns: match by attribute
  │     e.g., filterPattern: "vpc-id = vpc-xxx"
  │     Pros: flexible
  │     Cons: can match unexpected resources if filters are too broad
  └── All resources (DO NOT USE in production): match everything
        Pros: simple
        Cons: UNCONTROLLED BLAST RADIUS — can impact production
```

**Key implication:** the safest production FIS target is a tag-based
filter that requires an explicit opt-in tag (e.g., `FIS_Target=enabled`).
This prevents accidental targeting of resources that were not intended
to be part of the experiment. Resources without the tag are never
matched, even if the filter is misconfigured.

## Expert heuristic: stop conditions auto-abort when alarms fire (moved from SKILL.md)

Stop conditions are CloudWatch alarms that, when they transition to
ALARM state during the experiment, trigger FIS to auto-abort all running
actions and initiate rollback. Without a stop condition, FIS runs the
fault action to its full duration regardless of impact. Always configure
at least one stop condition that represents "the system is degraded
beyond acceptable limits" (e.g., CPU > 90%, error rate > 5%, latency
> 2000ms, HealthyHostCount < 1).

## Expert heuristic: IAM role must allow the specific fault action on target resources (moved from SKILL.md)

The FIS service role must have a trust policy that allows
`fis.amazonaws.com` to assume it, plus permissions scoped to the
specific fault action on the specific target resources (ideally scoped
by `Condition` on resource tags). The #1 cause of "experiment failed to
start" is a missing permission in the IAM role. FIS's error message is
often opaque ("FIS could not assume the role" or "permission denied").
Always verify the role has both the trust policy and the action-specific
permissions before creating the experiment template.

```text
IAM role permission matrix:
  aws:ec2:stop-instances        → ec2:StopInstances, ec2:StartInstances, ec2:DescribeInstances
  aws:ec2:terminate-instances   → ec2:TerminateInstances, ec2:DescribeInstances
  aws:ecs:drain-container-instances → ecs:ListContainerInstances, ecs:UpdateContainerInstancesState, ecs:DescribeContainerInstances
  aws:lambda:invoke             → lambda:InvokeFunction
  aws:network:disrupt-connectivity → ec2:CreateNetworkInterface, ec2:DeleteNetworkInterface, ec2:DescribeNetworkInterfaces + FIS network agent pass-role
  aws:rds:failover-db-cluster   → rds:FailoverDBCluster, rds:DescribeDBClusters
  aws:s3:pause-bucket-access    → s3:PutBucketAcl (or equivalent on the bucket)
  aws:cloudwatch:put-metric-data → cloudwatch:PutMetricData (account-wide)
```

## Step 8 — Recent features (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **Account-level targeting (2023-2024):** FIS added support for
  targeting resources across an account, enabling broader blast-radius
  experiments.
- **S3 bucket access pause (2023-2024):** `aws:s3:pause-bucket-access`
  action added for resilience testing (applications must handle S3
  unavailability).
- **CloudWatch metric injection (2023-2024):**
  `aws:cloudwatch:put-metric-data` action added for testing
  alarm-triggered auto-remediation without actually faulting a resource.
- **Network connectivity disruption enhancements (2023-2024):**
  `aws:network:disrupt-connectivity` now supports port-range filtering,
  direction filtering (ingress/egress), and packet delay/loss (not just
  full connectivity drop).
- **ECS container instance drain (2023-2024):**
  `aws:ecs:drain-container-instances` action added, allowing FIS to
  drain ECS container instances and test task rescheduling behavior.
- **FIS experiment template versioning (2024-2025):** Templates now
  support versioning, enabling safe updates to in-use templates without
  breaking running experiments.
- **Cross-account experiment execution (2024-2025):** Centralized chaos
  engineering teams can run experiments in workload accounts via IAM
  role assumption.
- **AWS Step Functions integration (2024-2025):** FIS experiments can
  be orchestrated as steps in a Step Functions state machine for
  complex multi-stage game-day scenarios.

