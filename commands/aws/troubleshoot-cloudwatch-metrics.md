---
name: troubleshoot-cloudwatch-metrics
description: >-
  Slash command for the cloudwatch-metrics-troubleshooter skill.
  Diagnoses missing or unexpected AWS CloudWatch metrics — wrong
  namespace, wrong dimensions, wrong statistic, INSUFFICIENT_DATA
  alarms, custom metric emission failures (PutMetricData denials,
  CloudWatch agent misconfig, malformed EMF blobs), EKS/ECS Container
  Insights missing, and CloudWatch RUM not collecting. Emits
  ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE with the specific
  failure category and offending config element.
skill: cloudwatch-metrics-troubleshooter
family: Management
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-cloudwatch-metrics

Invoke the `cloudwatch-metrics-troubleshooter` skill to diagnose a
CloudWatch metrics abnormality.

Read the skill at
`skills/cloudwatch-metrics-troubleshooter/SKILL.md` and follow its
diagnostic procedure to identify the root cause.

## When to use

- A CloudWatch metric is absent from a dashboard or query.
- `get-metric-statistics` returns empty for a metric you expect to
  exist.
- A metric value is wildly off from expectation (statistic or period
  mismatch).
- An alarm is persistently in `INSUFFICIENT_DATA`.
- A custom metric is not arriving (PutMetricData, CloudWatch agent,
  or EMF emission path).
- `ECS/ContainerInsights` or `ContainerInsights` namespace is empty
  for an ECS or EKS cluster.
- CloudWatch RUM is not collecting browser-side data.

## Invocation

```
/aws:troubleshoot-cloudwatch-metrics <namespace / metric / symptom description>
```

The skill will:

1. Identify the symptom category (METRIC_NOT_APPEARING,
   METRIC_VALUE_UNEXPECTED, INSUFFICIENT_DATA_ALARM,
   CUSTOM_METRIC_NOT_ARRIVING, CONTAINER_INSIGHTS_MISSING,
   RUM_NOT_COLLECTING).
2. Request (or run) `list-metrics` and `get-metric-statistics` to
   gather evidence.
3. Walk the category-specific diagnostic tree.
4. Cross-reference with the emitter (PutMetricData / agent / EMF),
   CloudTrail, and Container Insights / RUM configuration as required.
5. Map to the common root-cause catalog (10 patterns covering the
   most common CloudWatch metrics failures).
6. Verify the proposed fix via a corrected query, IAM simulation, or
   follow-up `list-metrics` call.
7. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <namespace / metric name / dimensions>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - list-metrics: <Namespace / MetricName / Dimensions>
  - get-metric-statistics: <Datapoints array or empty>
  - source logs (agent / EMF): <log line or absence>
  - describe-alarm (if applicable): <Period, EvaluationPeriods>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific query / config / IAM change + verification>
```

## Pre-flight

The skill requires the namespace and metric name at minimum. If only
a vague symptom is provided, the skill will run
`aws cloudwatch list-metrics` to surface candidate metrics; if no
identifying info is provided at all, the skill emits
`NEED_MORE_INFO`.

## References

- Skill: `skills/cloudwatch-metrics-troubleshooter/SKILL.md`
- Reference: `skills/cloudwatch-metrics-troubleshooter/references/diagnostic-decision-trees.md`
- Reference: `skills/cloudwatch-metrics-troubleshooter/references/emf-and-agent-validation.md`
- AWS docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html
