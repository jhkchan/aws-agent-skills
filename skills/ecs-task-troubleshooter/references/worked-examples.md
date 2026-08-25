# Worked Examples (load on demand) — ECS Task Troubleshooter

Secondary worked examples, moved verbatim from SKILL.md. The primary worked example (CannotPullContainerError / IMAGE_PULL_ENDPOINT) stays in SKILL.md.

---

## Worked example — INSUFFICIENT_DATA (moved from SKILL.md)

```text
TARGET: unknown
VERDICT: INSUFFICIENT_DATA
ROOT_CAUSE: UNKNOWN
REASON: Input is "ECS task failing in prod" with no cluster, service,
  task ARN, or symptom string; the category cannot be determined.
EVIDENCE:
  - Missing: cluster name or ARN
  - Missing: service name or task ARN
  - Missing: observed stoppedReason or service event string
REMEDIATION:
  1. Run aws ecs list-clusters and share the cluster ARN.
  2. Run aws ecs list-tasks --cluster <c> --desired-status STOPPED and
     share the most recent task ARN.
  3. Run aws ecs describe-tasks --cluster <c> --tasks <arn> and share
     the stoppedReason field.
```

