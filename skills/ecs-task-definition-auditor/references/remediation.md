# Remediation (load on demand) — ECS Task Definition Auditor

Per-verdict remediation recipes, moved verbatim from SKILL.md. The ordering principle stays in SKILL.md: always register a new revision instead of mutating the current one.

---

## Remediation guidance — per-verdict recipes (moved from SKILL.md)

### For PRIVILEGED — privileged container on EC2

1. Set `privileged: false` on the offending container definition.
2. If the container genuinely needs elevated access, add only the
   minimum required capability via `linuxParameters.capabilities.add`.
   Document why each capability is needed.
3. Register a new revision:
   `aws ecs register-task-definition --cli-input-json file://fixed-task-def.json`
4. Update the service:
   `aws ecs update-service --cluster <cluster> --service <service> --task-definition <family:new-revision>`
5. If the privileged container was running untrusted code or was
   internet-reachable, assume host compromise. Replace the EC2 instance
   and audit CloudTrail for anomalous activity during the exposure window.

### For SECRET_LEAK — plaintext secret in environment

1. Move the secret to the `secrets` array:
   ```json
   "secrets": [
     {
       "name": "DATABASE_PASSWORD",
       "valueFrom": "arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/db-password-AbCdEf"
     }
   ]
   ```
2. **Rotate the credential in the backing service** (database password,
   API key, etc.). The plaintext value persists in every historical
   task definition revision and in CloudTrail `RegisterTaskDefinition`
   events.
3. Verify the task role has `secretsmanager:GetSecretValue` (or
   `ssm:GetParameter` with decryption) for the referenced ARN.
4. Register a new revision and update the service.
5. After the new revision is stable, deregister all old revisions that
   contain the plaintext secret.

### For INSECURE — host network mode

1. Change `networkMode` from `host` to `awsvpc` (recommended) or
   `bridge`. `awsvpc` gives each task its own ENI + security group.
2. If switching to `awsvpc`, update the service's security group to
   allow the required inbound ports (previously bound on the host).
3. Update port mappings: `hostPort` is ignored on `awsvpc` (use
   `containerPort` only) or must be 0 on Fargate.

### For INSECURE — root user

1. Set `user` to a non-zero UID: `"user": "1000"` or `"user": "1000:1000"`.
2. Verify the container image creates this user in its Dockerfile
   (`RUN useradd -u 1000 appuser`). A named user that does not exist
   in the image silently falls back to root.
3. Set `readonlyRootFilesystem: true` for defense-in-depth. If the
   application writes temp files, mount a `tmpfs` volume:
   ```json
   "mountPoints": [{"containerPath": "/tmp", "sourceVolume": "tmp"}],
   "volumes": [{"name": "tmp", "host": null}]
   ```

### For INSECURE — dangerous capabilities

1. Remove the dangerous capability from `linuxParameters.capabilities.add`.
2. If the capability is genuinely required, document the justification
   and add compensating controls: `readonlyRootFilesystem: true`,
   `no-new-privileges:true`, and a restrictive AppArmor profile.
3. Prefer `SYS_PTRACE` (scoped) over `SYS_ADMIN` (broad) when choosing
   the minimum viable capability.

### For CONFIG_GAP — missing resource limits

1. Set task-level `cpu` and `memory` (required for Fargate):
   ```json
   "cpu": "512",
   "memory": "1GB"
   ```
2. Set container-level `memory` (hard limit) on each container for EC2
   launch type. Use `memoryReservation` for the soft limit.
3. Verify the values match Fargate's fixed CPU/memory combinations if
   applicable.

### For CONFIG_GAP — missing log configuration

1. Add `logConfiguration` to each container:
   ```json
   "logConfiguration": {
     "logDriver": "awslogs",
     "options": {
       "awslogs-group": "/ecs/<family>",
       "awslogs-region": "us-east-1",
       "awslogs-stream-prefix": "ecs"
     }
   }
   ```
2. Verify the execution role has `logs:CreateLogStream` and
   `logs:PutLogEvents`.

### For CONFIG_GAP — missing execution role

1. Create or reference an execution role with the managed policy
   `AmazonECSTaskExecutionRolePolicy` (covers ECR pull + CloudWatch Logs).
2. Set `executionRoleArn` on the task definition.

### For OK

1. No remediation required for the current posture.
2. Recommend `initProcessEnabled: true` for signal-handling correctness
   (defense-in-depth, not a security verdict driver).
3. Recommend `dockerSecurityOptions: ["no-new-privileges:true"]` to
   prevent setuid escalation.

