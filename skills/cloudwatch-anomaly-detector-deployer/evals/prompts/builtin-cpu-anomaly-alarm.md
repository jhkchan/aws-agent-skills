# Eval: builtin-cpu-anomaly-alarm

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — built-in AWS/EC2 CPUUtilization, 30 days of data, std dev 3, band-breach alarm with evaluation-periods 3, SNS notification

## Prompt

Create a CloudWatch Anomaly Detection model for the
CPUUtilization metric on EC2 instance i-abc1234567890 in
us-east-1. Namespace AWS/EC2. Stat Average, period 300 seconds.
The metric has been reporting for 30 days. Standard deviation
multiplier 3. Create a band-breach alarm that fires when CPU goes
above the upper band for 3 consecutive evaluation periods. SNS
topic arn arn:aws:sns:us-east-1:123456789012:anomaly-alerts.
Tags: Environment=production, Service=web-app.
