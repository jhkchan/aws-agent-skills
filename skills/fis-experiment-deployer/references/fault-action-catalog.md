# FIS Fault Action Catalog — Reference

Concrete action definitions, parameters, target shapes, and rollback
behavior for every FIS action supported by the fis-experiment-deployer
skill. Substitute `<REGION>`, `<ACCOUNT_ID>`, `<DURATION>`,
`<ALARM_NAME>`, `<ROLE_NAME>` as needed. Stored here so the main skill
body stays scannable.

## Action parameters — common fields

Every action in an FIS template has these envelope fields:

```json
{
  "actionId": "aws:ec2:stop-instances",
  "description": "Stop matched instances for 60s",
  "parameters": {"duration": "PT60S"},
  "targets": {"Instances": "target-instance-id"},
  "startAfter": [],
  "roleArn": "arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>"
}
```

`roleArn` at the action level overrides the template-level role. Use
the action-level role when different actions need different permission
scopes (e.g., EC2 vs. RDS).

## 1. EC2 stop-instances

```json
{
  "actionId": "aws:ec2:stop-instances",
  "parameters": {"duration": "PT60S"},
  "targets": {"Instances": "target-ec2-fis"}
}
```

**Effect:** Stops the matched instances, waits `duration`, then
attempts to start them. Rollback is best-effort — if start fails
(network/IAM drift), instances remain STOPPED.

**Target type:** `aws.ec2.instance`

**IAM permissions:**
- `ec2:StopInstances` (with tag condition recommended)
- `ec2:StartInstances` (for rollback)
- `ec2:DescribeInstances` (target resolution)

## 2. EC2 send-api-error

```json
{
  "actionId": "aws:ec2:send-api-error",
  "parameters": {
    "awsService": "ssm",
    "errorCode": "ThrottlingException",
    "duration": "PT2M",
    "percentage": 50
  },
  "targets": {"Roles": "target-iam-role"}
}
```

**Effect:** Returns the configured error code for `percentage` of API
calls made by the target IAM roles against `awsService`. Useful for
client retry/backoff validation without taking down the dependency.

**Target type:** `aws.iam.role`

**IAM permissions:**
- `iam:PassRole` (target resolution)
- `ec2:CreateNetworkInterface` (FIS injection mechanism)

## 3. EC2 terminate-instances

```json
{
  "actionId": "aws:ec2:terminate-instances",
  "parameters": {},
  "targets": {"Instances": "target-ec2-stateless"}
}
```

**Effect:** Terminates matched instances. Irreversible. The ASG
provisions replacements; ephemeral disk state is lost.

**Target type:** `aws.ec2.instance`

**WARNING:** Only use on stateless workloads with auto-replacement.
Always paired with a `[WARN]` note in the checklist.

**IAM permissions:**
- `ec2:TerminateInstances` (with tag condition mandatory)

## 4. ECS stop-task

```json
{
  "actionId": "aws:ecs:stop-task",
  "parameters": {"duration": "PT60S"},
  "targets": {"Tasks": "target-ecs-task"}
}
```

**Effect:** Stops matched ECS tasks. ECS reschedules per the service
definition (deployment minimum, etc.). No rollback — FIS does not
restart the same task.

**Target type:** `aws.ecs.task`

**IAM permissions:**
- `ecs:StopTask`
- `ecs:DescribeTasks` (target resolution)

## 5. EKS pod disruption (via SSM)

FIS does not expose a native `aws:eks:*` action in every region. The
canonical pattern uses SSM Run Command on the EKS worker node:

```json
{
  "actionId": "aws:ssm:start-automation-execution",
  "parameters": {
    "documentArn": "AWS-RunShellScript",
    "documentParameters": "{\"commands\":[\"kubectl delete pod -l app=critical --grace-period=0 --force\"]}",
    "duration": "PT1M"
  },
  "targets": {"Instances": "target-eks-worker"}
}
```

**Effect:** Runs kubectl on the worker node to delete pods matching
the label. The pod controller (Deployment/ReplicaSet) reschedules.

**Target type:** `aws.ec2.instance` (worker node)

**IAM permissions:**
- `ssm:SendCommand`
- `ssm:GetCommandInvocation`
- SSM document access

**Critical:** the worker node's SSM agent must run as a role with
EKS API permissions (or use a kubeconfig with cluster-admin). A
silent failure mode: SSM command succeeds but kubectl has no
permissions; pods are not disrupted. Verify in worker node logs.

## 6. Network disrupt-connectivity (SSM-based)

```json
{
  "actionId": "aws:ssm:start-automation-execution",
  "parameters": {
    "documentArn": "AWS-RunShellScript",
    "documentParameters": "{\"commands\":[\"tc qdisc add dev eth0 root netem delay 200ms 50ms loss 5%\"]}",
    "duration": "PT5M"
  },
  "targets": {"Instances": "target-app-instance"}
}
```

Variants:
- **Blackhole:** `iptables -I INPUT -s <DB_IP> -j DROP`
- **Latency:** `tc qdisc add dev eth0 root netem delay 200ms`
- **Loss:** `tc qdisc add dev eth0 root netem loss 5%`
- **Bandwidth cap:** `tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 400ms`

Rollback: FIS invokes SSM with the reverse command
(`tc qdisc del`, `iptables -D`). If the SSM agent is unreachable at
action end, the rules persist. Always have a manual rollback runbook
(`tc qdisc del dev eth0 root` and `iptables -F`).

## 7. RDS failover-db-cluster (Aurora)

```json
{
  "actionId": "aws:rds:failover-db-cluster",
  "parameters": {},
  "targets": {"Clusters": "target-aurora-cluster"}
}
```

**Effect:** Promotes a different Aurora instance to writer. Failover
takes 30-120 seconds. No rollback — the cluster stays promoted until
the next failover event.

**Target type:** `aws.rds.cluster`

**IAM permissions:**
- `rds:FailoverDBCluster`
- `rds:DescribeDBClusters` (target resolution)

**Critical:** confirm the cluster is in `AVAILABLE` state. A cluster
already mid-failover returns `ConflictException`.

## 8. Lambda invoke-async

```json
{
  "actionId": "aws:lambda:invoke-async",
  "parameters": {
    "functionArn": "arn:aws:lambda:<REGION>:<ACCOUNT_ID>:function:my-fn",
    "payload": "{\"test\":true}",
    "invocations": 10
  },
  "targets": {}
}
```

**Effect:** Invokes the Lambda function asynchronously
`invocations` times. Each invocation is fire-and-forget from FIS's
perspective; failures flow to the Lambda DLQ.

**IAM permissions:**
- `lambda:InvokeFunction` on the function ARN

## Target filter shapes

### Resource tags

```json
{
  "targetId": "target-ec2-fis",
  "resourceType": "aws.ec2.instance",
  "selectionMode": "ALL",
  "resourceTags": {"fis-target": "true"}
}
```

### Resource ARNs

```json
{
  "targetId": "target-specific-instance",
  "resourceType": "aws.ec2.instance",
  "selectionMode": "ALL",
  "resourceArns": ["arn:aws:ec2:<REGION>:<ACCOUNT_ID>:instance/i-0abc123def"]
}
```

### Filters

```json
{
  "targetId": "target-filtered",
  "resourceType": "aws.ec2.instance",
  "selectionMode": "COUNT(1)",
  "filters": [
    {"path": "State.Name", "values": ["running"]},
    {"path": "Tags.TagKey", "values": ["fis-target"]},
    {"path": "Tags.TagValue", "values": ["true"]}
  ]
}
```

`selectionMode` accepts `ALL`, `COUNT(n)`, `PERCENT(n)`. Use `COUNT(1)`
for single-resource drills; `PERCENT(10)` for canary-style partial
disruption. Avoid `ALL` with broad tags.

## Stop condition shape

```json
"stopConditions": [
  {"source": "aws:cloudwatch:alarm", "value": "arn:aws:cloudwatch:<REGION>:<ACCOUNT_ID>:alarm:<ALARM_NAME>"}
]
```

Multiple stop conditions are OR'd — any one going ALARM halts the
experiment. Verify each alarm has data (not INSUFFICIENT_DATA) and
that the FIS role has `cloudwatch:DescribeAlarms` on the ARN.
