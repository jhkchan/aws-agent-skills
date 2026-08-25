# EventBridge Scheduler Deployer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Mindset (moved from SKILL.md)

**One-line takeaway:** EventBridge Scheduler is a serverless
scheduler that invokes AWS targets at specified times. It creates
and manages its own IAM role for target invocation (you do NOT
pre-create the role). Flexible time windows reduce cost by batching
invocations within a window. Schedule groups enable bulk enable/
disable. One-time schedules auto-delete after completion if
configured.

Three misconceptions dominate EventBridge Scheduler misdesign at
provisioning time:

- **"I need to create an IAM role for the Scheduler to assume."**
  You do NOT. The Scheduler creates and manages its own IAM role
  automatically. You specify the target ARN and the Scheduler
  generates the appropriate permissions policy. The only role
  requirement is that the CALLER (you) must have
  `iam:PassRole` permission so the Scheduler can use the role it
  creates.

- **"Flexible time window OFF means immediate invocation."** It
  does NOT mean immediate — it means the Scheduler invokes at the
  exact schedule time. Setting the window to MAXIMUM means the
  Scheduler can invoke any time within the window (batching for
  cost optimization). The trade-off is precision vs cost: OFF is
  precise but more expensive; MAXIMUM is cheaper but less precise
  about exact invocation time.

- **"Schedule groups are just for organization."** They are NOT
  just labels. Groups enable bulk operations: you can enable or
  disable ALL schedules in a group with one API call. This is
  critical for maintenance windows, feature flags, and environment
  promotions. Without groups, you must toggle schedules one by one.

## Configuration dependency graph (moved from SKILL.md)

EventBridge Scheduler configurations are NOT independent. The IAM
role is auto-created per target type. The flexible time window
affects cost and precision. DLQ must exist before schedule creation.
Groups must exist before schedules are assigned. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Schedule group | Caller has scheduler:CreateScheduleGroup | group name is immutable (cannot rename); group CANNOT be deleted if it has schedules | group-level bulk enable/disable |
| Schedule (rate) | Target ARN exists; caller has scheduler:CreateSchedule + iam:PassRole | rate expression minimum is 1 minute; flexible time window must be >= rate for MAXIMUM mode | periodic target invocation |
| Schedule (cron) | Target ARN exists; caller has scheduler:CreateSchedule + iam:PassRole | cron expression uses UTC fields but timezone can be specified; cron is more precise than rate | precise-time target invocation |
| One-time schedule | Target ARN exists; schedule date/time in the future | one-time schedule with delete-after-completion=true is REMOVED after invocation — no history remains in the API | single-fire target invocation |
| Flexible time window (OFF) | Schedule rate or cron specified | OFF means exact-time invocation (higher cost per invocation) | precise scheduling |
| Flexible time window (MAXIMUM) | Schedule rate specified; window must be >= rate interval | MAXIMUM batches invocations within the window — reduces cost but invocation time is imprecise | cost-optimized scheduling |
| IAM role (target invocation) | Scheduler auto-creates; caller must have iam:PassRole | role is managed by Scheduler — do NOT manually edit or delete it | target invocation permissions |
| Retry policy | DLQ ARN (if configured); max retry count + max event age | retries use exponential backoff; after max retries, event goes to DLQ | error recovery |
| Dead-letter queue (DLQ) | SQS queue exists before schedule creation; caller has sqs permissions | DLQ receives failed invocations after retries are exhausted — messages persist until processed | error handling |
| Start/after time | Schedule created; start datetime in the future | schedule does NOT fire before the start time — it is effectively DISABLED until then | delayed activation |
| End/before time | Schedule created; end datetime in the future | schedule does NOT fire after the end time — it is effectively DISABLED after then | automatic deactivation |
| Target input (constant JSON) | Valid JSON string; target accepts the input format | input is passed verbatim to the target — invalid JSON causes invocation failure | parameterized invocation |

**The IAM-role-auto-creation row is the one a baseline model misses.**
A model that tries to pre-create a role for the Scheduler to assume
will create unnecessary complexity. The Scheduler handles role
creation and permission scoping automatically. The caller only needs
`iam:PassRole` to authorize the Scheduler to use the managed role.

**Cross-dependency gotchas:**
- The DLQ SQS queue MUST exist before the schedule is created. If
  the queue does not exist, schedule creation fails.
- The flexible time window MUST be >= the rate interval for MAXIMUM
  mode. If the window is smaller than the rate, the API rejects it.
- One-time schedules with `delete-after-completion=true` leave no
  trace in the API after firing. If you need audit history, set it
  to false or log externally.
- Schedule group deletion fails if the group contains schedules.
  Delete or move all schedules first.
- Timezone is specified per schedule, not per group. Two schedules
  in the same group can have different timezones.

## Recent features (2023-2026) (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **EventBridge Scheduler GA (2023-2024):** General availability of
  EventBridge Scheduler, providing a serverless, managed scheduler
  with no infrastructure to manage. Supports 200+ AWS target types
  via universal templates.

- **Schedule groups (2023-2024):** Group-level bulk operations for
  enable/disable, enabling maintenance window patterns and
  environment-level schedule management.

- **Timezone support (2023-2024):** Per-schedule timezone
  specification using IANA identifiers, eliminating the need to
  manually convert cron expressions to UTC.

- **One-time schedules with auto-delete (2023-2024):** One-time
  schedules can auto-delete after completion, preventing clutter
  in the schedule inventory.

- **Universal templates (2024-2025):** Expanded target templates
  covering Inspector, ECS RunTask, CodePipeline StartExecution,
  and more, simplifying target configuration.

- **Enhanced retry controls (2024-2025):** Granular retry policy
  with configurable max attempts and max event age, plus DLQ
  support for failed invocations.

- **Terraform provider maturity (2024-2025):** Full Terraform
  support for aws_scheduler_schedule and
  aws_scheduler_schedule_group, including flexible time window,
  retry policy, DLQ, and timezone.
