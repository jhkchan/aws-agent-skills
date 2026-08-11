# End-to-End Example: Enabling CloudWatch Application Signals on an ECS Fargate Java Service

A walkthrough showing how to use the
`cloudwatch-application-signals-deployer` skill from invocation
through verification. Mirrors the structured-eval pattern of shipping
a concrete worked example per skill.

---

## Scenario

You are enabling CloudWatch Application Signals on the `payments-api`
service running on ECS Fargate. The goal:

- Java 17 (Corretto) runtime
- Auto-instrumentation via ADOT Java agent + collector sidecar
- Task role `payments-api-task` with
  `CloudWatchApplicationSignalsReportServiceAccess` and
  `AWSXrayWriteOnlyAccess` attached
- X-Ray Default sampling rule `FixedRate=0.05`
- Service discovery via CloudMap namespace `payments.local`
- 99.9% availability SLO over 28 days rolling
- Multi-window burn-rate alarms

Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloudwatch-application-signals
```

Then paste the service enablement requirements.

### Option B: Natural language

```
You: "Enable CloudWatch Application Signals on the payments-api
      ECS Fargate service in us-east-1. Runtime: Java 17. Task
      role payments-api-task has both managed policies attached.
      X-Ray sampling FixedRate=0.05. ADOT sidecar pattern. Create
      a 99.9% availability SLO over 28 days rolling with burn-rate
      alarms. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy cloudwatch application signals"
```

Output:

```
[Phase: Deploy | Skills routed: cloudwatch-application-signals-deployer]

Primary route: cloudwatch-application-signals-deployer (score: 19)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SERVICE: payments-api
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Platform — ECS Fargate
  [✓]      Runtime — Java 17 (Corretto)
  [✓]      Auto-instrumentation — ADOT Java agent + collector sidecar
  [✓]      Application Signals role — arn:aws:iam::123456789012:role/payments-api-task (CloudWatchApplicationSignalsReportServiceAccess, AWSXrayWriteOnlyAccess)
  [✓]      Service name override — AWS_SERVICE_NAME=payments-api, AWS_APPLICATION_ENVIRONMENT=prod
  [✓]      X-Ray tracing — enabled, Default sampling FixedRate=0.05
  [✓]      Service discovery — CloudMap namespace payments.local
  [✓]      RED metrics — CloudWatch AWS/ApplicationSignals namespace receives Rate / Errors / Duration
  [✓]      Service map — node visible within 5-10 min of first trace
  [✓]      SLO — 99.9% availability over 28 days rolling
  [✓]      Burn-rate alarm — fast (5m, 14.4x), medium (1h, 6x), slow (6h, 3x)
VERIFICATION_COMMANDS:
  aws application-signals list-services --region us-east-1
  aws application-signals list-service-level-objectives --region us-east-1
  aws xray get-sampling-rules --region us-east-1
  aws iam list-attached-role-policies --role-name payments-api-task
  aws cloudwatch describe-alarms --alarm-name-prefix payments-api-slo
  aws cloudwatch list-metrics --namespace AWS/ApplicationSignals --dimensions Name=ServiceName,Value=payments-api
```

---

## Step 3 — Apply the IAM policies (if not yet attached)

```bash
aws iam attach-role-policy \
  --role-name payments-api-task \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchApplicationSignalsReportServiceAccess

aws iam attach-role-policy \
  --role-name payments-api-task \
  --policy-arn arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess

# Verify both attached
aws iam list-attached-role-policies --role-name payments-api-task \
  --query 'AttachedPolicies[].PolicyArn'
```

---

## Step 4 — Register the instrumented ECS task definition

The key additions to the task definition:

- The `aws-otel-collector` sidecar (must `START` before the app)
- The `payments-api` container with `JAVA_TOOL_OPTIONS` injecting the
  ADOT Java agent, plus `AWS_SERVICE_NAME`, `AWS_APPLICATION_ENVIRONMENT`,
  and `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`

```bash
# Step 5 of references/deployment-cli-commands.md has the full JSON
aws ecs register-task-definition \
  --cli-input-json file:///tmp/payments-api-task-def.json

aws ecs update-service \
  --cluster payments \
  --service payments-api \
  --task-definition payments-api:5
```

---

## Step 5 — Create the SLO via CloudFormation

```bash
aws cloudformation deploy \
  --stack-name payments-api-slo \
  --template-file /tmp/availability-slo.yaml \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

The CloudFormation template creates an
`AWS::ApplicationSignals::ServiceLevelObjective` resource bound to
`ServiceName=payments-api`, with rolling 28-day interval, 99.9%
attainment goal, and burn-rate rollups at MINUTE and HOUR intervals.

---

## Step 6 — Create the burn-rate alarms

```bash
SLO_ID=$(aws application-signals list-service-level-objectives \
  --query 'ServiceLevelObjectives[?Name==`payments-api-availability-slo`].Id' \
  --output text)

# Fast burn — 5-minute window, 14.4x threshold
aws cloudwatch put-metric-alarm \
  --alarm-name payments-api-slo-burn-fast \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=SLOId,Value=${SLO_ID} Name=RollupInterval,Value=MINUTE \
  --period 300 --evaluation-periods 1 \
  --threshold 14.4 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data noData \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:oncall-page

# (Repeat for medium 1h/6x and slow 6h/3x)
```

---

## Step 7 — Post-deployment verification

```bash
# Service discovered by Application Signals
aws application-signals list-services --region us-east-1

# SLO active
aws application-signals list-service-level-objectives --region us-east-1

# Burn-rate alarms created
aws cloudwatch describe-alarms --alarm-name-prefix payments-api-slo

# X-Ray traces are flowing
aws xray get-trace-summaries \
  --start-time $(date -u +%s --date='10 min ago') \
  --end-time $(date -u +%s) \
  --filter-expression 'service.id = "payments-api"'

# RED metrics published
aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --dimensions Name=ServiceName,Value=payments-api
```

Within 5-10 minutes of the first trace flow, the `payments-api` node
appears in the CloudWatch console under Application Signals → Service
map, with edges to downstream dependencies.

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| IAM policies | Often only `AWSXrayWriteOnlyAccess` | Both `CloudWatchApplicationSignalsReportServiceAccess` AND `AWSXrayWriteOnlyAccess` | Without `CloudWatchApplicationSignalsReportServiceAccess`, the agent runs but produces zero RED metrics — silent failure. |
| Service name | Container image name | `AWS_SERVICE_NAME=payments-api` env var | Without the env var, services collapse into one node ("SpringBootApp"), SLOs cannot bind. |
| Sampling rule | Often ignored | Verified `FixedRate >= 0.05` | 0% sampling blanks RED metrics entirely (Rate / Errors / Duration derive from traces). |
| SLO timing | SLO created before service discovered | SLO created after `list-services` confirms the node exists | Creating an SLO before discovery produces a CloudFormation rollback. |
| Burn-rate alarm period | Single alarm at SLO period | Multi-window: 5m/14.4x, 1h/6x, 6h/3x, 1d/1x | Multi-window catches both fast burns (page) and slow drains (ticket) without flapping. |
| Treat-missing-data | Default (`missing`) | `noData` | During deployments, RED metrics are absent — `breaching` triggers false pages. |
| ADOT collector config | Generic OTLP | `awsemf` exporter to CloudWatch + `awsxray` exporter | The collector must export to both X-Ray (for traces) and CloudWatch (for derived metrics). |

---

## Related artifacts

- **Skill definition:** `skills/cloudwatch-application-signals-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/cloudwatch-application-signals-deployer/references/deployment-cli-commands.md`
- **SLO and service discovery guide:** `skills/cloudwatch-application-signals-deployer/references/slo-and-service-discovery-guide.md`
- **Slash command:** `commands/aws/deploy-cloudwatch-application-signals.md`
- **Eval suite:** `skills/cloudwatch-application-signals-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudwatch-application-signals-deployer/eval/test-cases.yaml`
