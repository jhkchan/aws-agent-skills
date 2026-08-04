# Baseline (no-skill) response: privileged-ec2-sidecar

This file captures what a generic assistant produces WITHOUT the
ecs-task-definition-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, container-escape reasoning).

---

This ECS task definition has a container called "sidecar" with
`privileged: true` set. The `privileged` flag gives the container elevated
permissions on the host.

You should review whether the container really needs to be privileged. In
most cases, containers should not run in privileged mode. If it does need
extra capabilities, you can add specific ones via `linuxParameters`.

The container runs as user 1000 (non-root), has CPU and memory limits set,
and has logging configured. The network mode is bridge which is the
default Docker networking.
