# Baseline (no-skill) response: predictive-scaling-no-history-missing

This file captures what a generic assistant produces WITHOUT the
autoscaling-policy-deployer skill loaded. The contrast proves the skill
catches the missing-history prerequisite (predictive scaling needs
>= 24h of CloudWatch data) — the baseline provisions without checking.

---

Here's the predictive scaling policy:

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name new-launch-asg \
  --policy-name predictive-cpu \
  --policy-type PredictiveScaling \
  --predictive-scaling-configuration '{
    "MetricSpecifications": [{
      "TargetValue": 40.0,
      "PredefinedMetricPairSpecification": {
        "PredefinedMetricType": "ASGCPUUtilization",
        "ResourceLabel": ""
      }
    }],
    "Mode": "ForecastAndScale",
    "SchedulingBufferTime": 300,
    "MaxCapacityBreachBehavior": "IncreaseMaxCapacity",
    "MaxCapacityBuffer": 10
  }'
```

Predictive scaling will start forecasting your CPU usage and
pre-provisioning capacity before demand spikes. Verify with:

```bash
aws autoscaling describe-scaling-policies --auto-scaling-group-names new-launch-asg
```
