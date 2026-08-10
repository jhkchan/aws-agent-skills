---
name: troubleshoot-stepfunctions-execution
description: >-
  Slash command for the stepfunctions-execution-troubleshooter skill.
  Diagnoses AWS Step Functions execution failures across Standard and
  Express workflows — States.Runtime (invalid JSONPath), States.Timeout,
  States.TaskFailed (integration error), States.Permission /
  States.Permissions (IAM missing or cross-account), States.
  ParameterPathFailure, States.BranchFailed (Parallel / Map), States.ALL
  vs specific error catching, retry exhaustion (MaxAttempts), execution
  limits (Express 5 min vs Standard 1 year), and redrive eligibility.
  Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE with the specific
  failure category and offending config element.
skill: stepfunctions-execution-troubleshooter
family: AppIntegration
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-stepfunctions-execution

Invoke the `stepfunctions-execution-troubleshooter` skill to diagnose a
Step Functions execution failure.

Read the skill at
`skills/stepfunctions-execution-troubleshooter/SKILL.md` and follow its
diagnostic procedure to identify the root cause.

## When to use

- A Step Functions execution FAILED with `States.Runtime`,
  `States.Timeout`, `States.TaskFailed`, `States.Permission`,
  `States.ParameterPathFailure`, or `States.BranchFailed`.
- A Retry block exhausted `MaxAttempts` and the execution failed
  terminally.
- A Catcher did not catch an error you expected it to.
- An Express workflow hit the 5-minute `ExecutionTimedOut` cap.
- A Standard workflow was throttled (`ExecutionThrottled`,
  `ThrottledStateTransition` CloudWatch metrics).
- You want to redrive a failed Standard execution and need to verify
  eligibility.

## Invocation

```
/aws:troubleshoot-stepfunctions-execution <state machine / execution / symptom description>
```

The skill will:

1. Identify the symptom category (RUNTIME_ERROR, TASK_TIMEOUT,
   TASK_FAILED, PERMISSION_DENIED, PARAMETER_PATH_FAILURE,
   BRANCH_FAILED, RETRY_EXHAUSTED, CATCH_MISCONFIGURED,
   EXECUTION_LIMIT_HIT, REDRIVE_CANDIDATE).
2. Request the failing execution ARN and `describe-execution` /
   `get-execution-history` output.
3. Walk the category-specific diagnostic tree.
4. Cross-reference with the ASL definition, IAM role simulation,
   integration logs, and CloudWatch Metrics as required.
5. Map to the common root-cause catalog (10 patterns covering the
   most common Step Functions failures).
6. Verify the proposed fix via the `test-state` API or a verification
   execution before applying.
7. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <state machine ARN> / <execution ARN>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - describe-execution: <error + cause>
  - get-execution-history: <failing state + event>
  - describe-state-machine: <ASL snippet>
  - CloudWatch Metrics: <ExecutionsFailed / ExecutionThrottled>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific ASL / IAM / Catcher change + verification>
```

## Pre-flight

The skill requires the state machine ARN and either the execution ARN
or the execution name. If only the state machine ARN is provided, the
skill will run `aws stepfunctions list-executions --status FAILED` to
surface recently-failed executions. If the user provides only a vague
symptom with no identifying info, the skill emits `NEED_MORE_INFO`.

## References

- Skill: `skills/stepfunctions-execution-troubleshooter/SKILL.md`
- Reference: `skills/stepfunctions-execution-troubleshooter/references/error-catalog-and-decision-tree.md`
- Reference: `skills/stepfunctions-execution-troubleshooter/references/diagnostic-commands.md`
- AWS docs: https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
