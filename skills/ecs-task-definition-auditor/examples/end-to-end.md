# End-to-end usage scenario: ecs-task-definition-auditor

A walkthrough showing the skill auditing a legacy EC2 task definition that
has multiple findings across all five dimensions (PRIVILEGED, SECRET_LEAK,
INSECURE, CONFIG_GAP), demonstrating severity aggregation, the
worst-verdict-wins rule, and the register-new-revision remediation workflow.

## Input (user prompt)

> Audit this ECS task definition before we migrate it to Fargate. I want
> to know every security issue.

```json
{
  "family": "legacy-data-pipeline",
  "networkMode": "host",
  "requiresCompatibilities": ["EC2"],
  "containerDefinitions": [
    {
      "name": "etl-runner",
      "image": "111111111111.dkr.ecr.us-east-1.amazonaws.com/etl-runner:old",
      "privileged": true,
      "user": "root",
      "environment": [
        {"name": "DB_HOST", "value": "prod-db.cluster-abc.us-east-1.rds.amazonaws.com"},
        {"name": "DB_PASSWORD", "value": "Hunter2#Production!"},
        {"name": "S3_BUCKET", "value": "etl-output-prod"}
      ],
      "readonlyRootFilesystem": false,
      "linuxParameters": {
        "capabilities": {
          "add": ["SYS_ADMIN", "NET_ADMIN"]
        }
      }
    }
  ]
}
```

## Expected behavior

1. **Step 1 (Privileged):** Container "etl-runner" has `privileged: true`
   on EC2 launch type → **PRIVILEGED**. Full host kernel access.

2. **Step 2 (Secret leak):** `DB_PASSWORD` found in plaintext `environment`
   → **SECRET_LEAK**. Credential permanently committed in the task
   definition JSON.

3. **Step 3 (Insecure):** `networkMode: host` → INSECURE (HOST_NETWORK).
   `user: root` → INSECURE (ROOT_USER). `readonlyRootFilesystem: false`
   → INSECURE sub-finding (WRITEABLE_ROOTFS). `SYS_ADMIN` + `NET_ADMIN`
   in capabilities.add → INSECURE (DANGEROUS_CAPABILITY).

4. **Step 4 (Config gap):** No task-level or container-level `cpu`/
   `memory` → CONFIG_GAP (NO_MEMORY_LIMIT, NO_CPU_LIMIT). No
   `logConfiguration` → CONFIG_GAP (NO_LOGGING). No `executionRoleArn`
   → CONFIG_GAP (MISSING_EXECUTION_ROLE).

5. **Step 5 (Aggregation):** Worst verdict wins → **PRIVILEGED**.

## Expected output

```text
TASK: legacy-data-pipeline
VERDICT: PRIVILEGED
REASON: Container "etl-runner" has privileged: true on an EC2 launch type —
full host kernel access bypassing all Docker security isolation (Step 1).
Additionally, DB_PASSWORD is stored in plaintext environment, the task uses
host networking, runs as root, adds SYS_ADMIN/NET_ADMIN capabilities, and
has no resource limits or logging.
FINDINGS:
  - [PRIVILEGED] Container "etl-runner" has privileged: true on EC2 (Step 1)
  - [SECRET_LEAK] DB_PASSWORD found in plaintext environment (Step 2)
  - [INSECURE] networkMode: host — no network namespace isolation (Step 3a)
  - [INSECURE] user: root — container runs as UID 0 (Step 3b)
  - [INSECURE] SYS_ADMIN + NET_ADMIN added via capabilities (Step 3c)
  - [INSECURE] readonlyRootFilesystem: false — writeable root filesystem (Step 3d)
  - [CONFIG_GAP] No task-level or container-level memory hard limit (Step 4a)
  - [CONFIG_GAP] No task-level or container-level CPU limit (Step 4a)
  - [CONFIG_GAP] No logConfiguration on container "etl-runner" (Step 4b)
  - [CONFIG_GAP] Missing executionRoleArn (Step 4c)
REMEDIATION:
  1. Set privileged: false. Remove SYS_ADMIN and NET_ADMIN from
     capabilities.add. Drop ALL capabilities and add back only the minimum
     needed.
  2. Move DB_PASSWORD to the secrets array referencing a Secrets Manager
     ARN. Rotate the credential — it persists in every historical revision.
  3. Change networkMode to awsvpc (required for Fargate migration anyway).
  4. Set user to a non-zero UID (e.g., "1000:1000").
  5. Set readonlyRootFilesystem: true. Add tmpfs mounts for temp paths.
  6. Set task-level cpu and memory. Add container-level memory (hard limit).
  7. Add logConfiguration with awslogs driver.
  8. Add executionRoleArn with AmazonECSTaskExecutionRolePolicy.
  9. Register a new revision and update the service to use it.
```

## Remediation workflow

1. **Register a new revision** with all fixes applied.
2. **Update the ECS service** to use the new revision.
3. **Rotate DB_PASSWORD** in the database — the plaintext value persists
   in the old revision JSON indefinitely.
4. **Deregister** the old revision after the new deployment stabilizes.
5. **Replace the EC2 instance** — a privileged container may have already
   escaped to the host. Audit CloudTrail for anomalous activity during the
   exposure window.
