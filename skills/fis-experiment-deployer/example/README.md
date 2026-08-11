# End-to-End Example: FIS EC2 Stop-Canary Experiment

A walkthrough showing how to use the `fis-experiment-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are running a game day and want to validate that stopping a
single canary EC2 instance triggers your alerting and auto-recovery.
You need:

- An FIS experiment template targeting the canary (tag
  `fis-target=true`, populated with exactly 1 instance)
- Action: `aws:ec2:stop-instances` for 60 seconds
- Stop condition: CloudWatch alarm `fis-stop-error-rate` on
  application error rate
- IAM execution role scoped to the tag (second line of defense)
- Logging to S3 + CloudWatch Logs
- 2-minute budget (2x the action duration for rollback margin)

Region: us-east-1
Account: 111111111111

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-fis-experiment
```

Then paste the experiment requirements.

### Option B: Natural language

```
You: "Provision an FIS experiment template called ec2-stop-canary
      targeting instances tagged fis-target=true (1 instance). Stop
      for 60s with alarm fis-stop-error-rate as stop condition.
      budgetDuration 2 minutes."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create fis experiment template"
```

Output:

```
[Phase: Deploy | Skills routed: fis-experiment-deployer]
Primary route: fis-experiment-deployer (score: 21)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
EXPERIMENT_TEMPLATE: ec2-stop-canary (action: aws:ec2:stop-instances, target: fis-target=true)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Intent + blast radius: Stop one canary instance for 60s to validate auto-recovery, blast radius 1 instance
  [✓] Target scoped: resourceTags fis-target=true (1 instance i-0abc123)
  [✓] Action(s): aws:ec2:stop-instances (duration PT60S)
  [✓] Stop condition(s): fis-stop-error-rate (state: OK)
  [✓] IAM role: fis-execution-role (fis trust, ec2:StopInstances + StartInstances scoped to aws:ResourceTag/fis-target=true, cloudwatch:DescribeAlarms on fis-stop-error-rate)
  [✓] Logging: S3 fis-logs-111111111111 + CloudWatch Logs /aws/fis/ec2-stop-canary
  [✓] budgetDuration: PT2M (rationale: 2x the 60s stop action for rollback margin)
VERIFICATION_COMMANDS:
  aws fis get-experiment-template --id EXT-AAAA1111
  aws ec2 describe-instances --filters Name=tag:fis-target,Values=true --query 'Reservations[0].Instances[0].InstanceId'
  aws cloudwatch describe-alarms --alarm-names fis-stop-error-rate --query 'MetricAlarms[0].StateValue'
  aws iam get-role-policy --role-name fis-execution-role --policy-name fis-execution-policy
  aws logs describe-log-groups --log-group-name-prefix /aws/fis/ec2-stop-canary
```

---

## Step 3 — Provisioning commands

```bash
# Step 5: Create the IAM execution role (with tag conditions)
aws iam create-role \
  --role-name fis-execution-role \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"fis.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }'

aws iam put-role-policy \
  --role-name fis-execution-role \
  --policy-name fis-execution-policy \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["ec2:StopInstances","ec2:StartInstances"],"Resource":"arn:aws:ec2:us-east-1:111111111111:instance/*","Condition":{"StringEquals":{"aws:ResourceTag/fis-target":"true"}}},
      {"Effect":"Allow","Action":["ec2:DescribeInstances","ec2:DescribeInstanceStatus"],"Resource":"*"},
      {"Effect":"Allow","Action":"cloudwatch:DescribeAlarms","Resource":"arn:aws:cloudwatch:us-east-1:111111111111:alarm:fis-stop-error-rate"},
      {"Effect":"Allow","Action":["logs:CreateLogStream","logs:PutLogEvents"],"Resource":"arn:aws:logs:us-east-1:111111111111:log-group:/aws/fis/ec2-stop-canary:*"}
    ]
  }'

# Step 6: Create the CloudWatch Logs log group BEFORE the experiment starts
aws logs create-log-group \
  --log-group-name /aws/fis/ec2-stop-canary \
  --retention-in-days 30

# Step 7-8: Create the experiment template
aws fis create-experiment-template \
  --description "Stop canary EC2 for 60s to validate auto-recovery" \
  --role-arn arn:aws:iam::111111111111:role/fis-execution-role \
  --targets '{
    "Instances":{"resourceType":"aws.ec2.instance","selectionMode":"ALL","resourceTags":{"fis-target":"true"}}
  }' \
  --actions '{
    "stop":{"actionId":"aws:ec2:stop-instances","parameters":{"duration":"PT60S"},"targets":{"Instances":"Instances"}}
  }' \
  --stop-conditions '[
    {"source":"aws:cloudwatch:alarm","value":"arn:aws:cloudwatch:us-east-1:111111111111:alarm:fis-stop-error-rate"}
  ]' \
  --log-configuration '{
    "logSchemaVersion":2,
    "cloudWatchLogsConfiguration":{"logGroupArn":"arn:aws:logs:us-east-1:111111111111:log-group:/aws/fis/ec2-stop-canary"},
    "s3Configuration":{"bucketName":"fis-logs-111111111111","prefix":"experiments/ec2-stop-canary/"}
  }' \
  --budget-duration PT2M
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the template is stored
aws fis get-experiment-template --id <TEMPLATE_ID>

# Confirm only 1 instance matches the target tag
aws ec2 describe-instances --filters Name=tag:fis-target,Values=true \
  --query 'Reservations[*].Instances[*].InstanceId'

# Confirm the alarm is in OK state (will fire if error rate spikes)
aws cloudwatch describe-alarms --alarm-names fis-stop-error-rate \
  --query 'MetricAlarms[0].StateValue'

# Dry-run: start + immediately stop to validate IAM + target resolution
EXP_ID=$(aws fis start-experiment --experiment-template-id <TEMPLATE_ID> --client-token $(date +%s) --query 'experiment.id' --output text)
sleep 15
aws fis stop-experiment --id $EXP_ID
aws fis get-experiment --id $EXP_ID --query 'experiment.state'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Target tag scoping | `Resource: "*"` on ec2:StopInstances | Tag condition `aws:ResourceTag/fis-target=true` on action API | If the target filter is misconfigured (e.g., broadened later), the IAM tag condition is the second line of defense. |
| Stop-condition alarm permission | Assumed; alarm ARN configured but FIS role has no DescribeAlarms | Explicit `cloudwatch:DescribeAlarms` on alarm ARN in role policy | FIS fails open on missing alarm permission — the experiment runs to budget with the stop condition silently inactive. |
| Log group creation | Skipped | `aws logs create-log-group` before template apply | FIS does not create the log group. A missing group means silent logging failure. |
| Budget rationale | PT5M default | PT2M with cited rationale | A 2-minute budget bounds the failure window if rollback fails. |
| Target population check | Skipped | `describe-instances` count confirmation | A drift in tag population (e.g., 100 instances tagged fis-target=true) would massively expand blast radius. |

---

## Related artifacts

- **Skill definition:** `skills/fis-experiment-deployer/SKILL.md`
- **Fault action catalog:** `skills/fis-experiment-deployer/references/fault-action-catalog.md`
- **IAM + logging templates:** `skills/fis-experiment-deployer/references/iam-and-logging-templates.md`
- **Slash command:** `commands/aws/deploy-fis-experiment.md`
- **Eval suite:** `skills/fis-experiment-deployer/evals/evals.json`
- **Legacy test cases:** `skills/fis-experiment-deployer/eval/test-cases.yaml`
