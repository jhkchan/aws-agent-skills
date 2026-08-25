# Worked Examples (load on demand) — CloudWatch Logs Not-Ingesting Troubleshooter

Secondary worked examples moved verbatim from SKILL.md; the primary worked example (IAM_PERMISSIONS on Lambda execution role) remains inline in SKILL.md. Loaded on demand.

---

## Worked example — SEQUENCE_TOKEN collision (moved from SKILL.md)

```text
TARGET: /ecs/app
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Two ECS tasks share the same log_stream_name ("app") in the
  firelensConfiguration; each task's PutLogEvents call uses a token
  from the previous successful call by either task, producing
  InvalidSequenceTokenException on every other call.
LAYER: SEQUENCE_TOKEN
EVIDENCE:
  - Symptom: approximately 50% of PutLogEvents calls from the ECS
    tasks return InvalidSequenceTokenException; the other half
    succeed.
  - Probe: aws logs describe-log-streams --log-group-name /ecs/app
    shows a single stream "app" with rapidly-changing
    uploadSequenceToken.
  - Probe: the ECS task definition's firelensConfiguration uses a
    hardcoded log_stream_name "app" with no task-id suffix.
  - Passing: the ECS task role has logs:PutLogEvents allowed (not an
    IAM issue); retention is Never expire (not a retention issue).
REMEDIATION:
  1. Change the firelensConfiguration log_stream_name to include the
     task id (e.g., "app-{task_id}") so each task writes to its own
     stream.
  2. Redeploy the task definition.
  3. Verify with describe-log-streams — there should be N streams
     (one per running task) and no InvalidSequenceTokenException.
```
