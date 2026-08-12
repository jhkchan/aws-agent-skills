# Eval: insufficient-training-data

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — only 3 days of historical data; ML model needs >= 15 data points at configured period (roughly 2 weeks at 5-min resolution for reliable baseline)

## Prompt

Create a CloudWatch Anomaly Detection model for the
CPUUtilization metric on EC2 instance i-newinstance999 in
us-east-1. Namespace AWS/EC2. Stat Average, period 300. The
instance was launched 3 days ago so the metric only has about
800 data points at 5-min resolution. Standard deviation 3. Create
a band-breach alarm with SNS topic
arn:aws:sns:us-east-1:123456789012:anomaly-alerts.
