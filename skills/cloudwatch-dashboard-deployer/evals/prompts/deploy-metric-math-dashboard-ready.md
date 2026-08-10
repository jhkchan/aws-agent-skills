# Eval prompt: deploy-metric-math-dashboard-ready

Plan the following CloudWatch dashboard creation and emit the standard
VERDICT block (DASHBOARD, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, WIDGETS, SHARING, NOTES).

Operation: create
Dashboard name: prod-alb-error-rate
Region: us-east-1
Account: 111111111111
Widgets:
  - type: metric
    title: ALB 5xx Error Rate (%)
    metric_math:
      m1: AWS/ApplicationELB, HTTPCode_ELB_5XX_Count, Sum, LoadBalancer=app/prod-alb/1234567890
      m2: AWS/ApplicationELB, RequestCount, Sum, LoadBalancer=app/prod-alb/1234567890
      e1: m1/m2*100
    period: 60
    position: x=0, y=0, w=24, h=6

```json
{
  "MetricChecks": {
    "get-metric-statistics.AWS/ApplicationELB.HTTPCode_ELB_5XX_Count.LoadBalancer=app/prod-alb/1234567890": {
      "datapoints": 60,
      "Sum": 12.5
    },
    "get-metric-statistics.AWS/ApplicationELB.RequestCount.LoadBalancer=app/prod-alb/1234567890": {
      "datapoints": 60,
      "Sum": 5000.0
    }
  },
  "ExistingDashboard": null
}
```
