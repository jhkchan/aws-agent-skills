# Diagnostic and Monitoring Commands — kinesis-stream-deployer

CloudWatch monitoring command listings moved verbatim from SKILL.md Step 7.

## CloudWatch alarm setup (Step 7)

**Alarm: IteratorAgeMilliseconds:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "Kinesis-my-stream-IteratorAge-High" \
  --metric-name GetRecords.IteratorAgeMilliseconds \
  --namespace AWS/Kinesis --statistic Maximum --period 300 \
  --threshold 300000 --comparison-operator GreaterThanThreshold \
  --dimensions Name=StreamName,Value=my-data-stream \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts-topic \
  --region us-east-1
```

**Alarm: WriteProvisionedThroughputExceeded (provisioned mode only):**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "Kinesis-my-stream-WriteThrottle-High" \
  --metric-name WriteProvisionedThroughputExceeded \
  --namespace AWS/Kinesis --statistic Sum --period 300 \
  --threshold 0 --comparison-operator GreaterThanThreshold \
  --dimensions Name=StreamName,Value=my-data-stream \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts-topic \
  --region us-east-1
```

