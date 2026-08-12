# Actions and Targets — FIS Template Deployer

Deep reference on the eight FIS-supported fault actions (action IDs,
required parameters, durations, rollback behavior), target selection
mechanisms (resource tags vs IDs vs filters, selectionMode semantics),
and action-target binding. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## The eight fault actions

### aws:ec2:stop-instances

Stops the targeted EC2 instances, then optionally restarts them after
a delay.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `startAfter` | list of duration strings | No | Duration after which to restart the instances (e.g., `["5m"]`). If omitted, instances stay stopped until manually started or the experiment is aborted. |

**Targets:** `Instances` (resourceType: `aws:ec2:instance`).

**Rollback:** instances are restarted when the action completes or the
experiment is aborted. If the stop condition fires, FIS restarts the
instances as part of rollback.

**Required IAM permissions:**
- `ec2:StopInstances`
- `ec2:StartInstances` (for rollback)
- `ec2:DescribeInstances`

### aws:ec2:terminate-instances

Terminates the targeted EC2 instances. **Irreversible** — terminated
instances cannot be restored. Only use when an Auto Scaling Group (or
equivalent replacement mechanism) will provision replacements.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `completeAfter` | list of duration strings | No | Duration after which the action is considered complete (the instances are already terminated; this just controls the action state transition). |

**Targets:** `Instances` (resourceType: `aws:ec2:instance`).

**Rollback:** NONE. Termination is irreversible. Ensure an ASG replaces
the instances.

**Required IAM permissions:**
- `ec2:TerminateInstances`
- `ec2:DescribeInstances`

### aws:ecs:drain-container-instances

Sets the targeted ECS container instances to DRAINING state, which
causes ECS to reschedule tasks off the instance.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `duration` | duration string | Yes | How long to keep the instances in DRAINING state (e.g., `"5m"`). |

**Targets:** `ContainerInstances` (resourceType:
`aws:ecs:container-instance`).

**Rollback:** container instances are set back to ACTIVE state when the
action completes or the experiment is aborted.

**Required IAM permissions:**
- `ecs:ListContainerInstances`
- `ecs:UpdateContainerInstancesState`
- `ecs:DescribeContainerInstances`

### aws:lambda:invoke

Invokes the targeted Lambda function with a custom payload. Useful for
running custom chaos/fault logic (e.g., injecting errors into a
specific service).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `functionArn` | string | Yes | ARN of the Lambda function to invoke. |
| `functionPayload` | string | No | JSON payload to pass to the function. |

**Targets:** `Function` (resourceType: `aws:lambda:function`), or no
target if `functionArn` is specified directly in parameters.

**Rollback:** NONE (the function's effects must be self-reverting or
monitored separately).

**Required IAM permissions:**
- `lambda:InvokeFunction`

### aws:network:disrupt-connectivity

Disrupts network connectivity between availability zones, subnets, or
security groups. Uses the FIS network agent (a network interface
injected into the target VPC).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `duration` | duration string | Yes | How long to disrupt connectivity. |
| `scope` | string | No | Scope of disruption (e.g., `between-availability-zones`, `availability-zone`, `subnet`). |
| `portRanges` | string | No | Port ranges to disrupt (e.g., `"80-443"`). |
| `sourcePorts` | string | No | Source port ranges to disrupt. |
| `direction` | string | No | `ingress` or `egress`. |
| `disrupt` | string | No | Type of disruption: `all`, `loss`, `delay`, `duplicate`, `corrupt`. |

**Targets:** `Subnets` or `AvailabilityZones` (depending on scope).

**Rollback:** the FIS network agent is removed and connectivity is
restored when the action completes or the experiment is aborted.

**Required IAM permissions (network agent):**
- `ec2:CreateNetworkInterface`
- `ec2:DeleteNetworkInterface`
- `ec2:DescribeNetworkInterfaces`
- `ec2:CreateNetworkInterfacePermission`
- `iam:PassRole` (to pass the FIS network agent role)

### aws:rds:failover-db-cluster

Triggers a failover of the targeted Aurora DB cluster, promoting a
different reader instance to writer.

**Parameters:** none (uses the target cluster).

**Targets:** `Clusters` (resourceType: `aws:rds:cluster`).

**Rollback:** NONE. Failover is a real cluster topology change. The
cluster remains in the post-failover state after the experiment.

**Required IAM permissions:**
- `rds:FailoverDBCluster`
- `rds:DescribeDBClusters`

### aws:s3:pause-bucket-access

Temporarily pauses access to the targeted S3 bucket, making it
temporarily unavailable.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `duration` | duration string | Yes | How long to pause bucket access. |

**Targets:** `Buckets` (resourceType: `aws:s3:bucket`).

**Rollback:** bucket access is restored when the action completes or
the experiment is aborted.

**Required IAM permissions:**
- `s3:PutBucketAcl` (or equivalent bucket-modification permission)

### aws:cloudwatch:put-metric-data

Pushes custom metric data to CloudWatch. Useful for testing alarm-
triggered auto-remediation without actually faulting a resource.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `namespace` | string | Yes | CloudWatch metric namespace. |
| `metricName` | string | Yes | CloudWatch metric name. |
| `value` | string | Yes | Metric value to push. |

**Targets:** none (CloudWatch metrics are account-scoped).

**Rollback:** the metric data remains in CloudWatch (it is not
"rolled back"). Use a short metric period to minimize lasting impact.

**Required IAM permissions:**
- `cloudwatch:PutMetricData`

## Target selection deep dive

### Resource tags (RECOMMENDED)

Resource tags are the safest scoping mechanism. They bind to a stable,
auditable attribute and require explicit opt-in.

```json
"targets": {
  "target-instances": {
    "resourceType": "aws:ec2:instance",
    "resourceTags": {
      "FIS_Target": "enabled",
      "Environment": "staging"
    },
    "selectionMode": "COUNT(1)"
  }
}
```

**All tag key-value pairs must match** (logical AND). A resource with
`FIS_Target=enabled` but `Environment=production` will NOT match the
target above.

### Resource IDs

Resource IDs are precise but brittle. Use only when the resource IDs
are stable (e.g., RDS cluster ARNs, S3 bucket names).

```json
"targets": {
  "target-cluster": {
    "resourceType": "aws:rds:cluster",
    "resourceIds": [
      "arn:aws:rds:us-east-1:123456789012:cluster:aurora-prod-cluster"
    ],
    "selectionMode": "COUNT(1)"
  }
}
```

### selectionMode reference

| Mode | Behavior |
|---|---|
| `COUNT(n)` | Target exactly n matched resources, chosen randomly. |
| `ALL` | Target all matched resources. **Avoid in production.** |
| `PERCENT(n)` | Target n% of matched resources, chosen randomly. |

## Action sequencing

By default, actions in a template run concurrently. To sequence them:

```json
"actions": {
  "action-1": {
    "actionId": "aws:ec2:stop-instances",
    "parameters": { "startAfter": ["5m"] },
    "targets": { "Instances": "target-instances" }
  },
  "action-2": {
    "actionId": "aws:cloudwatch:put-metric-data",
    "parameters": { "namespace": "FIS-Test", "metricName": "StopCompleted", "value": "1" },
    "startAfter": ["action-1"]
  }
}
```

`startAfter: ["action-1"]` means action-2 starts only after action-1
completes (or is aborted).
