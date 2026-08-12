# Eval prompt: sequence-token-collision-shared-stream

Diagnose the CloudWatch Logs not-ingesting scenario for the following
ECS deployment. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: ECS tasks log to CloudWatch Logs group
`/ecs/sequence-token-collision-shared-stream`. Approximately 50% of
`PutLogEvents` calls return `InvalidSequenceTokenException`. The other
50% succeed. Events are being lost on the failing calls.

```text
LogGroup: /ecs/sequence-token-collision-shared-stream
Source: ECS tasks (firelensConfiguration)
Number of running ECS tasks: 2 (task A and task B), each writing to
  the same log stream.

aws logs describe-log-streams --log-group-name
/ecs/sequence-token-collision-shared-stream:
  single log stream named "app" exists
  uploadSequenceToken: changes rapidly (different value on each call)

ECS task definition firelensConfiguration:
  log_stream_name: "app"  (hardcoded — no task_id suffix)

ECS task role IAM simulation:
  logs:CreateLogStream on /ecs/*: ALLOWED
  logs:PutLogEvents on /ecs/*: ALLOWED

CloudWatch metrics for the log group (last hour):
  IncomingBytes: present but lower than expected
Retention: Never expire
```

Each PutLogEvents call (after the first) must include the
`sequenceToken` returned by the previous successful call to the same
log stream. The token serialises writes; two concurrent emitters
writing to the same stream will collide, each seeing the other's token
as stale. The fix is one writer per stream (use `{task_id}` in the
stream name), not refreshing the token.
