# Error Handling (load on demand) — ECS Task Troubleshooter

Task-definition validation error patterns (Step 9) and the per-ROOT_CAUSE remediation table, moved verbatim from SKILL.md.

---

## Step 9: Task definition validation errors (moved from SKILL.md)

`register-task-definition` or `run-task` returns
`ClientException` / `InvalidParameterException`. Common patterns:

| Error string | ROOT_CAUSE |
|---|---|
| `Container.instanceType is not compatible with cpu/memory` | Invalid Fargate CPU/memory combo |
| `Invalid parameter at 'containerDefinitions[0].portMappings'` | Port conflict between containers |
| `requiresCompatibilities lists FARGATE but networkMode is not awsvpc` | Network mode mismatch |
| `Task role or execution role ARN is malformed or does not exist` | Role ARN invalid |

**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: CONFIG_DEFINITION_INVALID`.
Fix: correct the offending field in the task definition.

## Remediation guidance (moved from SKILL.md)

| ROOT_CAUSE | Specific fix |
|---|---|
| `RESOURCE_INIT_ENI` | Enable ENI trunking on supported EC2 instance types, OR migrate to Fargate. |
| `RESOURCE_INIT_SUBNET_IP` | Create new wider subnets and update the service `networkConfiguration.awsvpcConfiguration.subnets`. Do NOT resize in-use subnets. |
| `IMAGE_PULL_AUTH` | Attach `AmazonECSTaskExecutionRolePolicy` to the execution role; for cross-account, add a statement to the ECR repo policy granting the task's execution role ARN. |
| `IMAGE_PULL_ENDPOINT` | Create the three required VPC endpoints (ecr.api, ecr.dkr interface + s3 gateway). Interface endpoints need a SG that allows inbound 443 from the task's SG. |
| `IMAGE_PULL_SIZE` | Rebuild the image below 10 GB uncompressed (target < 1 GB for fast cold starts). |
| `CAPACITY_PLACEMENT` | Add container instances or scale the capacity provider's ASG; confirm instance attributes match the task's `requiresCompatibilities`. |
| `CAPACITY_DEREGISTERED` | Reconnect the ECS agent (`systemctl restart ecs`) or replace the instance via the ASG; check `/var/log/ecs/ecs-agent.log`. |
| `CONFIG_TASK_ROLE` / `CONFIG_EXECUTION_ROLE` | Add the missing IAM permission via `iam put-role-policy` or attach a managed policy; verify with `simulate-principal-policy`. |
| `HEALTH_CHECK` | Align `healthCheckPath` in the target group to the application's route; ensure the task's SG allows the ALB's SG on the container port. |
| `OOM` | Raise `memory` (hard limit) in the container definition, or fix the memory leak in the application code. |
| `PLATFORM_VERSION` | Pin `platformVersion` to the previous working version; avoid `LATEST` in production. |
| `CIRCUIT_BREAKER` | Fold to the underlying category via Steps 1–6; the circuit breaker is never the actual root cause. |
| `CONFIG_DEFINITION_INVALID` | Correct the offending field in the task definition; re-register via `aws ecs register-task-definition`. |

