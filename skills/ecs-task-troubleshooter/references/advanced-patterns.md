# Advanced Patterns (load on demand) — ECS Task Troubleshooter

The expert heuristic (stoppedReason-first mapping) and the configuration dependency graph, moved verbatim from SKILL.md.

---

## Expert heuristic (moved from SKILL.md)

> **`stoppedReason` is the primary diagnostic surface.** Every stopped
> ECS task carries a `stoppedReason` string and, in nearly every case,
> a per-container `containers[].reason` with the exit code. Read these
> BEFORE opening CloudWatch Logs. The string maps deterministically to
> a root-cause category:
>
> - `ResourceInitializationError` → ENI / subnet / ECR endpoint layer
> - `CannotPullContainerError` → ECR auth / endpoint / size layer
> - `EC2InstanceStateError` → deregistered container instance
> - `Essential container in task exited` → application / OOM / task role
>   (fold via `exitCode`)
> - `GoOffline` / `TaskFailed` from circuit breaker → fold to underlying
>
> **For `awsvpc` mode, ENI attachment requires a free IP in every
> subnet the task is placed in.** A `/28` subnet has 11 usable IPs; a
> burst of 12 tasks exhausts the pool. ENI trunking on EC2 launch type
> raises the per-instance ENI cap but is NOT automatic — the trunk must
> be requested and the instance must support it (`ecs.awsvpc-trunking`
> instance attribute).
>
> **For private subnets, ECR pull requires the ECR interface endpoint
> (`ecr.api`, `ecr.dkr`) AND the S3 gateway endpoint.** The execution
> role must grant `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`,
> `ecr:GetAuthorizationToken`. Without the endpoints, Fargate cannot
> authenticate to ECR; without the role, the pull returns 401/403.

## Configuration dependency graph (moved from SKILL.md)

```
                       task definition
                             │
            ┌────────────────┼───────────────────┐
            ▼                ▼                   ▼
       taskRole        executionRole        containerDefinitions
       (runtime        (ECS agent /         (image, cpu, memory,
        AWS creds)     Fargate pulls          healthCheck, ports,
                       image + writes         secrets, entryPoint)
                       logs)
                             │
                             ▼
              ┌──────────────┴───────────────┐
              ▼                              ▼
        ECR repo policy              CloudWatch Logs
        (cross-account grants        (execution role needs
        for the function account)    logs:CreateLogStream +
                                     logs:PutLogEvents on the
                                     log group)
                             │
                             ▼
                       service
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
        launch type    capacity        network config
        (Fargate /     provider        (awsvpc → ENI in
         EC2)          strategy        subnet → needs free IP
                        placement       + SG; bridge/none →
                        constraints     host ENI)
                             │
                             ▼
                       subnet / VPC
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
        free IP count   route table      VPC endpoints
        (per /28 etc)   (NAT / IGW /    (ecr.api, ecr.dkr
                         TGW)             interface + s3
                                          gateway required for
                                          private subnets)
```

Read top-down: a task failure is a broken edge or broken node in this
graph. The diagnostic tree walks the graph from the symptom down.

