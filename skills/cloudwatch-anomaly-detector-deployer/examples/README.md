# End-to-End Example: CloudWatch Anomaly Detection Deployment

A walkthrough showing how to use the
`cloudwatch-anomaly-detector-deployer` skill from invocation through
verification. Mirrors the structured-eval pattern of shipping a
concrete worked example per skill.

---

## Scenario

You are deploying a CloudWatch Anomaly Detection model on an EC2
instance's CPUUtilization metric with a band-breach alarm. The
deployment needs:

- Namespace: AWS/EC2
- Metric: CPUUtilization
- Dimension: InstanceId=i-abc1234567890
- Stat: Average
- Period: 300 seconds (5 min)
- Historical data: 30 days (sufficient for ML baseline)
- Std dev multiplier: 3 (default — balanced)
- Alarm: band-breach on upper band, 3 evaluation periods
- SNS: arn:aws:sns:us-east-1:123456789012:anomaly-alerts
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-anomaly-detector
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CloudWatch anomaly detection model for CPUUtilization
      on i-abc1234567890 in us-east-1. Stat Average, period 300.
      30 days of historical data. Std dev 3. Band-breach alarm with
      3 evaluation periods. SNS anomaly-alerts."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create anomaly detection model"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ANOMALY_DETECTION: AWS/EC2/CPUUtilization [InstanceId=i-abc1234567890] (TRAINED)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Metric: AWS/EC2/CPUUtilization [InstanceId=i-abc1234567890]
  [✓] Historical data: 8640 data points at 300s (need >= 15)
  [✓] Metric compatibility: PASS (regular data, diurnal pattern)
  [✓] Stat: Average
  [✓] Period: 300 seconds (5 min)
  [✓] Std dev multiplier: 3 (default — balanced)
  [✓] Detector state: TRAINED
  [✓] Band breach alarm: cpu-anomaly-breach-i-abc123 (upper, evaluation-periods=3)
  [✓] SNS notification: arn:aws:sns:us-east-1:123456789012:anomaly-alerts
  [✓] Recovery to OK: enabled (ok-actions configured)
  [✓] Cross-account: single-account (123456789012)
  [✓] Composite alarm: none (standalone anomaly alarm)
  [✓] Metric type: built-in (AWS/EC2)
VERIFICATION_COMMANDS:
  aws cloudwatch describe-anomaly-detectors --namespace AWS/EC2 --region us-east-1
  aws cloudwatch describe-alarms --alarm-names cpu-anomaly-breach-i-abc123 --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --statistics Average --period 300 --start-time <15d-ago> --end-time <now> --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the anomaly detector
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" \
  --period 300 \
  --configuration '{"StandardDeviation": 3}' \
  --region us-east-1

# Step 2: Wait for detector to reach TRAINED state (up to 15 min)
aws cloudwatch describe-anomaly-detectors \
  --namespace "AWS/EC2" \
  --query 'AnomalyDetectors[0].State' \
  --region us-east-1 --output text
# Expected: TRAINED (not LEARNING)

# Step 3: Create the band-breach alarm using metric math
aws cloudwatch put-metric-alarm \
  --alarm-name "cpu-anomaly-breach-i-abc123" \
  --alarm-description "CPU utilization anomaly breach for i-abc1234567890" \
  --evaluation-periods 3 \
  --datapoints-to-alarm 3 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data "breaching" \
  --metrics '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization","Dimensions":[{"Name":"InstanceId","Value":"i-abc1234567890"}]},"Period":300,"Stat":"Average"}},
    {"Id":"e1","Expression":"ANOMALY_DETECTION_BAND(m1)","Label":"Band"},
    {"Id":"e2","Expression":"IF(m1 > e1, 1, 0)","Label":"BreachAbove","ReturnData":true}
  ]' \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:anomaly-alerts" \
  --region us-east-1

# Step 4: Tag the alarm (optional)
aws cloudwatch tag-resource \
  --resource-arn "arn:aws:cloudwatch:us-east-1:123456789012:alarm:cpu-anomaly-breach-i-abc123" \
  --tags Key=Environment,Value=production Key=Service,Value=web-app \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify detector exists and is TRAINED
aws cloudwatch describe-anomaly-detectors \
  --namespace "AWS/EC2" \
  --query 'AnomalyDetectors[*].{Namespace:Namespace,Metric:MetricName,State:State,StdDev:Configuration.StandardDeviation}' \
  --region us-east-1 --output table

# Verify alarm configuration
aws cloudwatch describe-alarms \
  --alarm-names "cpu-anomaly-breach-i-abc123" \
  --query 'MetricAlarms[0].{Name:AlarmName,State:StateValue,EvaluationPeriods:EvaluationPeriods,Actions:AlarmActions}' \
  --region us-east-1 --output table

# Verify metric has sufficient data (last 15 days)
aws cloudwatch get-metric-statistics \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --statistics Average \
  --period 300 \
  --start-time $(date -u -v-15d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Datapoints | length(@)' --output text --region us-east-1
# Expected: >= 4032 (15 days × 288 points/day)
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Training data depth | Not checked | >= 15 data points verified before deployment | ML model needs ~2 weeks for reliable baseline; without it detector stays LEARNING |
| Std dev multiplier | Default, unexplained | Explicitly set with rationale | Lower = more sensitive; must be tuned per metric volatility |
| Alarm metric math | Static threshold | ANOMALY_DETECTION_BAND metric math expression | Band-breach alarm requires comparing metric to the dynamic band, not a static value |
| Evaluation-periods | 1 (single point) | 3 (consecutive points) | Single-point evaluation causes flapping; 3+ periods reduces false positives |
| Recovery notification | No ok-actions | ok-actions configured | Recovery-to-OK should notify operators for alarm lifecycle visibility |
| Metric compatibility | Not checked | Regular data pattern verified | Sparse/irregular metrics produce poor baselines; not all metrics work |

---

## Related artifacts

- **Skill definition:** `skills/cloudwatch-anomaly-detector-deployer/SKILL.md`
- **Sensitivity and tuning guide:** `skills/cloudwatch-anomaly-detector-deployer/references/sensitivity-and-tuning.md`
- **Alarms and composite guide:** `skills/cloudwatch-anomaly-detector-deployer/references/alarms-and-composite.md`
- **Slash command:** `commands/aws/deploy-anomaly-detector.md`
- **Eval suite:** `skills/cloudwatch-anomaly-detector-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudwatch-anomaly-detector-deployer/eval/test-cases.yaml`
