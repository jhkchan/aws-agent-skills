---
name: troubleshoot-devops-guru
description: >-
  Slash command for the devops-guru-troubleshooter skill. Diagnoses
  Amazon DevOps Guru insights across Proactive (anomalous behavior) and
  Reactive (operational issue) categories. Covers severity (High/Medium/
  Low), resource coverage (CloudFormation, Auto Scaling groups, ALB,
  RDS, DynamoDB, Lambda, ECS, CodeBuild), analysis categories
  (performance, availability, cost, configuration), recommendation
  evaluation, false positive suppression, and the latest DevOps Guru
  for RDS/CodeBuild/Lambda and server-side encryption analysis.
  Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE with the specific
  insight category and root cause.
skill: devops-guru-troubleshooter
family: Management
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-devops-guru

Invoke the `devops-guru-troubleshooter` skill to diagnose a DevOps Guru
insight.

Read the skill at
`skills/devops-guru-troubleshooter/SKILL.md` and follow its diagnostic
procedure to identify the root cause.

## When to use

- A DevOps Guru insight is OPEN (Proactive or Reactive) and you need to
  determine the root cause.
- You want to evaluate whether to implement a DevOps Guru recommendation
  or apply a different fix.
- You need to suppress a false-positive insight with a documented
  rationale (not just console "dismiss").
- You are onboarding DevOps Guru to a new resource set and need to
  understand the insight surface.
- You need to correlate a Proactive insight with deployment history,
  CloudTrail events, or CloudWatch metrics.
- You are investigating DevOps Guru for RDS, Lambda, CodeBuild, or
  server-side encryption analysis (2024-2025 features).

## Invocation

```
/aws:troubleshoot-devops-guru <insight ID / symptom / describe-insight output>
```

The skill will:

1. Capture the insight ID, region, and the supplied diagnostic evidence
   (describe-insight, list-anomalies-for-insight, list-recommendations,
   CloudTrail correlation).
2. Classify the insight type (PROACTIVE vs REACTIVE).
3. Read the severity (HIGH / MEDIUM / LOW) and resource category.
4. Identify the analysis category (PERFORMANCE, AVAILABILITY, COST,
   CONFIGURATION).
5. Correlate anomalies with CloudTrail events and deployment history in
   the [T0-2h, T0] window.
6. Evaluate the recommendation against the root cause (implement /
   different fix / suppress / escalate).
7. Emit the standard VERDICT block.

## Output shape

```text
INSIGHT: <insight ID> in <region> — <InsightType + InsightSeverity + Name>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <InsightCategory> — <specific root cause>
EVIDENCE:
  - describe-insight: <InsightType, Severity, Status, Name>
  - list-anomalies-for-insight: <anomaly name + source + deviation>
  - list-recommendations: <recommendation category + text>
  - CloudWatch correlation: <metric + datapoint>
  - CloudTrail correlation: <event + time + user>
RESOURCE_CATEGORY: #<N>
ANALYSIS_CATEGORY: <PERFORMANCE | AVAILABILITY | COST | CONFIGURATION>
REMEDIATION: <exact action + verification + monitoring>
```

## Pre-flight

The skill requires the insight ID and the region. If only a partial
symptom is provided, the skill runs `aws devops-guru list-insights
--status-filter AnyOpenInsights` to surface recently-opened insights.
If the user provides only a vague symptom with no insight ID, the skill
emits `NEED_MORE_INFO`.

## References

- Skill: `skills/devops-guru-troubleshooter/SKILL.md`
- Reference: `skills/devops-guru-troubleshooter/references/diagnostic-commands.md`
- Reference: `skills/devops-guru-troubleshooter/references/insight-catalog-and-decision-tree.md`
- AWS docs: https://docs.aws.amazon.com/devops-guru/latest/userguide/welcome.html
