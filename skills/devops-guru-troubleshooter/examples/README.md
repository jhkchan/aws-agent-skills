# End-to-End Example: DevOps Guru Insight Triage

A walkthrough showing how to use the `devops-guru-troubleshooter` skill
from invocation through remediation. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are investigating a Proactive HIGH insight on an Application Load
Balancer. The insight reports increased latency starting at 14:35Z.
You need to:

- Classify the insight (Proactive vs Reactive)
- Identify the resource category and analysis category
- Correlate the anomaly with deployment history
- Determine the root cause
- Decide whether to implement the recommendation or a different fix

Insight ID: `x-1234abcd`
Region: `us-east-1`
Account: `111111111111`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:troubleshoot-devops-guru
```

Then paste the insight ID and the diagnostic evidence.

### Option B: Natural language

```
You: "Diagnose DevOps Guru insight x-1234abcd in us-east-1. The insight
      is PROACTIVE HIGH with the name 'Increased latency on ALB
      app/my-alb', StartTime 2026-08-09T14:35Z. The anomaly shows
      TargetResponseTime p99 elevated from 200ms baseline to 1800ms.
      A CodeDeploy deployment occurred at 14:32Z."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "diagnose devops guru insight"
```

Output:

```
[Phase: Troubleshoot | Skills routed: devops-guru-troubleshooter]

Primary route: devops-guru-troubleshooter (score: 22)
```

---

## Step 2 — Skill produces the ROOT_CAUSE_FOUND block

```text
INSIGHT: x-1234abcd in us-east-1 — PROACTIVE / HIGH / Increased latency on ALB app/my-alb
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: PERFORMANCE — CodeDeploy deployment at 2026-08-09T14:32Z (revision abc123) introduced a regression causing ALB TargetResponseTime p99 to spike from 200ms to 1800ms; RDS connection pool exhaustion (50 -> 380) is the downstream effect
EVIDENCE:
  - describe-insight: PROACTIVE, HIGH, OPEN, StartTime 2026-08-09T14:35Z
  - list-anomalies-for-insight: TargetResponseTime p99 200ms -> 1800ms; DatabaseConnections 50 -> 380; CPUUtilization 92%
  - list-recommendations: AGGREGATE_OF_METRICS — "Investigate the backend service for increased processing time." (generic, addresses symptom not root cause)
  - CloudTrail: CodeDeploy event at 14:32Z, 3 minutes before insight StartTime (strong correlation)
RESOURCE_CATEGORY: ALB + RDS (downstream)
ANALYSIS_CATEGORY: PERFORMANCE
REMEDIATION:
  1. Roll back the CodeDeploy deployment to the previous revision
  2. Verify ALB TargetResponseTime returns to baseline (<300ms) within 10 minutes
  3. Fix the regression in revision abc123 before redeploying; add a CloudWatch alarm on p99 TargetResponseTime > 500ms
```

---

## Step 3 — Diagnostic commands the skill used

The skill generated these CLI commands from
`references/diagnostic-commands.md`:

```bash
# 1. Describe the insight
aws devops-guru describe-insight --region us-east-1 \
  --insight-id x-1234abcd

# 2. List anomalies (the metric deviations)
aws devops-guru list-anomalies-for-insight --region us-east-1 \
  --insight-id x-1234abcd \
  --start-time-range '{From=2026-08-09T14:00:00Z,To=2026-08-09T15:30:00Z}'

# 3. List recommendations
aws devops-guru list-recommendations --region us-east-1 \
  --insight-id x-1234abcd

# 4. CloudTrail change-correlation (2h before insight StartTime)
aws cloudtrail lookup-events \
  --start-time 2026-08-09T12:35:00Z \
  --end-time 2026-08-09T14:35:00Z \
  --query 'Events[*].[EventTime,Username,EventName,ResourceName]' \
  --output table

# 5. CloudWatch metric correlation
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/my-alb/1234567890 \
  --start-time 2026-08-09T14:00:00Z \
  --end-time 2026-08-09T15:30:00Z \
  --period 300 --statistics Average,p99
```

---

## Step 4 — Remediation and verification

```bash
# 1. Roll back the CodeDeploy deployment
aws deploy stop-deployment --deployment-id d-ABCD1234 --auto-rollback-true

# 2. Verify ALB latency returns to baseline (within 10 minutes)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/my-alb/1234567890 \
  --start-time 2026-08-09T15:30:00Z \
  --end-time 2026-08-09T15:40:00Z \
  --period 60 --statistics Average \
  --query 'Datapoints[*].[Timestamp,Average]' --output table

# 3. Re-check insight status (expect RESOLVED within ~1 hour after fix)
aws devops-guru describe-insight --region us-east-1 \
  --insight-id x-1234abcd \
  --query 'ProactiveInsight.Status'
```

---

## What the skill catches that a naive diagnosis misses

| Step | Naive diagnosis | Skill output | Why the skill is right |
|---|---|---|---|
| Insight interpretation | Reads the insight Name as the root cause | Treats the Name as a symptom; correlates with deployment history | The insight describes the anomaly, not the cause |
| Recommendation evaluation | Auto-applies the "investigate backend" recommendation | Notes it is generic (AGGREGATE_OF_METRICS) and addresses the symptom | Recommendations are heuristic; the root cause is the code regression |
| Change-correlation | Skips the deployment history check | Cross-references CloudTrail and CodeDeploy in [T0-2h, T0] | ~70% of Proactive insights correlate with a recent code/config change |
| Resource mapping | Treats ALB as the only affected resource | Identifies RDS as the downstream resource (connection pool exhaustion) | The RDS anomaly is a downstream effect of the application regression |
| Remediation | Recommends scaling out | Recommends rollback (addresses root cause) | Scaling masks the regression; rollback restores service immediately |

---

## Related artifacts

- **Skill definition:** `skills/devops-guru-troubleshooter/SKILL.md`
- **Diagnostic commands:** `skills/devops-guru-troubleshooter/references/diagnostic-commands.md`
- **Insight catalog + decision tree:** `skills/devops-guru-troubleshooter/references/insight-catalog-and-decision-tree.md`
- **Slash command:** `commands/aws/troubleshoot-devops-guru.md`
- **Eval suite:** `skills/devops-guru-troubleshooter/evals/evals.json`
- **Legacy test cases:** `skills/devops-guru-troubleshooter/eval/test-cases.yaml`
