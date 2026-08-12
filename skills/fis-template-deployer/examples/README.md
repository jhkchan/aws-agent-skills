# End-to-End Example: FIS Experiment Template Deployment

A walkthrough showing how to use the `fis-template-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an AWS Fault Injection Simulator (FIS) experiment
template that stops one EC2 instance tagged for chaos testing in
staging, with a CloudWatch CPU-high alarm as a stop condition (auto-
abort safety net) and an IAM role scoped to the fault action on tagged
resources. The experiment needs:

- Action: aws:ec2:stop-instances (startAfter 5m)
- Target: EC2 instances tagged FIS_Target=enabled AND Environment=staging (COUNT 1)
- Stop condition: CloudWatch alarm FIS-CPU-High (>90% for 1 min)
- IAM role: FISExperimentRole (trust fis.amazonaws.com; ec2:StopInstances on tag FIS_Target=enabled)
- Log group: /aws/fis/stop-instance-experiment
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-fis-template
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a FIS experiment template to stop one EC2 instance
      tagged FIS_Target=enabled in staging. Stop condition
      FIS-CPU-High alarm. Role FISExperimentRole."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a fis experiment template"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
FIS_TEMPLATE: EXTVAR123456 — aws:ec2:stop-instances on EC2 instances tagged FIS_Target=enabled
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Action: aws:ec2:stop-instances — startAfter: 5m
  [✓] Target: aws:ec2:instance via tags {FIS_Target=enabled, Environment=staging} (selectionMode: COUNT(1))
  [✓] Stop condition: arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-CPU-High
  [✓] IAM role: arn:aws:iam::123456789012:role/FISExperimentRole (trust: fis.amazonaws.com; permissions: ec2:StopInstances on tag:FIS_Target=enabled)
  [✓] Log group: /aws/fis/stop-instance-experiment
  [✓] Resource tags verified: FIS_Target=enabled on 3 instances in staging
  [✓] Duration: 5m (stop, then auto-restart)
  [✓] Region: us-east-1
  [✓] Tags: Environment=staging, ExperimentType=HA-Test
VERIFICATION_COMMANDS:
  aws fis get-experiment-template --id EXTVAR123456 --region us-east-1
  aws fis get-experiment --id EXP1234567 --region us-east-1
  aws cloudwatch describe-alarms --alarm-names FIS-CPU-High
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the CloudWatch alarm (stop condition prerequisite)
aws cloudwatch put-metric-alarm \
  --alarm-name "FIS-CPU-High" \
  --metric-name "CPUUtilization" --namespace "AWS/EC2" \
  --statistic "Average" --period 60 --threshold 90.0 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=AutoScalingGroupName,Value=my-asg" \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:fis-alerts" \
  --region us-east-1

# Step 2: Create the IAM role with trust policy
aws iam create-role --role-name FISExperimentRole \
  --assume-role-policy-document file://trust-policy.json --region us-east-1

aws iam put-role-policy --role-name FISExperimentRole \
  --policy-name FISExperimentPermissions \
  --policy-document file://permissions-policy.json

# Step 3: Create the log group
aws logs create-log-group \
  --log-group-name "/aws/fis/stop-instance-experiment" --region us-east-1

# Step 4: Create the experiment template
TEMPLATE_ID=$(aws fis create-experiment-template \
  --cli-input-json file://experiment-template.json \
  --region us-east-1 \
  --query 'experimentTemplate.id' --output text)

# Step 5: Wait ~30s for IAM propagation, then start the experiment
EXPERIMENT_ID=$(aws fis start-experiment \
  --experiment-template-id "$TEMPLATE_ID" --region us-east-1 \
  --query 'experiment.id' --output text)

# Step 6: Monitor experiment state (pending → running → completed | aborted)
aws fis get-experiment --id "$EXPERIMENT_ID" \
  --region us-east-1 --query 'experiment.state'
```

---

## Step 4 — Post-experiment verification

```bash
# Experiment template — verify configuration
aws fis get-experiment-template --id "$TEMPLATE_ID" --region us-east-1

# Experiment state — should be completed or aborted
aws fis get-experiment --id "$EXPERIMENT_ID" --region us-east-1

# Verify stopped instances were restarted (rollback)
aws ec2 describe-instances \
  --filters "Name=tag:FIS_Target,Values=enabled" \
  --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' \
  --region us-east-1 --output table

# Stop condition alarm state (should be OK if experiment passed)
aws cloudwatch describe-alarms \
  --alarm-names "FIS-CPU-High" \
  --query 'MetricAlarms[0].StateValue' --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Stop condition | Not configured | CloudWatch alarm stop condition | Without it, FIS runs to completion regardless of impact; no safety net |
| Target scoping | All instances | Tag-based (FIS_Target=enabled) | Tags are the safest scope; explicit opt-in prevents accidental production targeting |
| IAM permissions | Blanket ec2:* | Scoped via Condition on resource tags | Least privilege; over-permissive role violates security |
| IAM trust policy | Often forgotten | fis.amazonaws.com trust | Without it, experiment fails to start with opaque error |
| Alarm ordering | Template created before alarm | Alarm created first | Template creation fails if the alarm ARN does not exist |
| Log group | Not configured | CloudWatch Logs log group | Without it, experiment state changes are not retained for debugging |

---

## Related artifacts

- **Skill definition:** `skills/fis-template-deployer/SKILL.md`
- **Actions and targets guide:** `skills/fis-template-deployer/references/actions-and-targets.md`
- **IAM and stop conditions guide:** `skills/fis-template-deployer/references/iam-and-stop-conditions.md`
- **Slash command:** `commands/aws/deploy-fis-template.md`
- **Eval suite:** `skills/fis-template-deployer/evals/evals.json`
- **Legacy test cases:** `skills/fis-template-deployer/eval/test-cases.yaml`
