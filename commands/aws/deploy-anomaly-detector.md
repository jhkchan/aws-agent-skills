---
description: Deploy a CloudWatch Anomaly Detection model on an AWS metric with production-grade defaults (ML baseline, std dev tuning, band-breach alarm, cross-account support, composite integration). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create anomaly detection"
  - "deploy anomaly detector"
  - "cloudwatch anomaly detection"
  - "anomaly band breach alarm"
  - "tune anomaly sensitivity"
  - "anomaly detector std dev"
  - "anomaly detection custom metric"
  - "cross-account anomaly detection"
  - "anomaly detection band"
  - "metric math anomaly"
  - "ml baseline metric"
routes_to: cloudwatch-anomaly-detector-deployer
---

# /aws:deploy-anomaly-detector

Activate the `cloudwatch-anomaly-detector-deployer` skill and deploy a
CloudWatch Anomaly Detection model with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Anomaly detection model (ML baseline — random cut forest)
2. Metric compatibility check (not all metrics supported)
3. Configuration (stat, period, dimensions)
4. Sensitivity tuning (std dev multiplier — default 3)
5. Band visualization (ANOMALY_DETECTION_BAND metric math)
6. Alarm on band breach (upper/lower/either)
7. Assessment period and training data (2-week minimum)
8. Recovery to normal state (OK actions)
9. Cross-account anomaly detection (monitoring/source model)
10. Composite alarm integration (anomaly AND/OR threshold)
11. Custom metrics vs built-in support
12. Recent features (cross-account GA, high-resolution, composite)

## When to use

- You need to create a CloudWatch Anomaly Detection model on a metric.
- You want to alert when a metric deviates from its expected pattern.
- You are tuning anomaly detection sensitivity (std dev multiplier).
- You need cross-account anomaly detection (central monitoring account).
- You want to combine anomaly detection with static thresholds (composite).
- You need band visualization for a CloudWatch metric.

## When NOT to use

- **Static-threshold alarms without anomaly detection** — use standard
  CloudWatch alarm skills.
- **CloudWatch Logs Insights anomaly detection** — different feature.
- **Metric streaming to Kinesis** — different pipeline.
- **Prometheus/Grafana anomaly detection** — not CloudWatch.

## How to invoke

### Slash command

```
/aws:deploy-anomaly-detector
```

Then provide: metric namespace, metric name, dimensions, stat
(Average/Sum/p99), period, std dev multiplier, SNS topic ARN,
evaluation-periods, and whether cross-account or composite alarm
integration is needed.

### Natural language

Any of these routes to the same skill:

- "create an anomaly detection model for CPU utilization"
- "set up anomaly detection on my custom metric"
- "tune the std dev multiplier for my anomaly detector"
- "create a cross-account anomaly detection model"
- "combine anomaly detection with a static threshold alarm"

### CLI routing

```bash
node cli/bin/cli.js route "create anomaly detection model"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create CloudWatch
Anomaly Detection models. The output checklist feeds into verification
pipelines and downstream monitoring skills.

## Example

```
You: /aws:deploy-anomaly-detector

     Create a CloudWatch Anomaly Detection model for
     CPUUtilization on i-abc1234567890 in us-east-1.
     Stat Average, period 300. 30 days of data. Std dev 3.
     Band-breach alarm with 3 evaluation periods.
     SNS anomaly-alerts.

Skill:
  ANOMALY_DETECTION: AWS/EC2/CPUUtilization [InstanceId=i-abc1234567890]
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Historical data: 8640 data points at 300s (need >= 15)
    [✓] Std dev multiplier: 3
    [✓] Band breach alarm: cpu-anomaly-breach (evaluation-periods=3)
    [✓] SNS: arn:aws:sns:us-east-1:123456789012:anomaly-alerts
  VERIFICATION_COMMANDS:
    aws cloudwatch describe-anomaly-detectors --namespace AWS/EC2 --region us-east-1
    aws cloudwatch describe-alarms --alarm-names cpu-anomaly-breach --region us-east-1
```

## References

- Skill definition: `skills/cloudwatch-anomaly-detector-deployer/SKILL.md`
- Sensitivity and tuning guide: `skills/cloudwatch-anomaly-detector-deployer/references/sensitivity-and-tuning.md`
- Alarms and composite guide: `skills/cloudwatch-anomaly-detector-deployer/references/alarms-and-composite.md`
- Eval suite: `skills/cloudwatch-anomaly-detector-deployer/evals/evals.json`
