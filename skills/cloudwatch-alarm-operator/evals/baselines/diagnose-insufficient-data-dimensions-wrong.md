# Baseline (no-skill) response: diagnose-insufficient-data-dimensions-wrong

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-operator skill loaded.

---

Your alarm is stuck in INSUFFICIENT_DATA, which usually means the
metric isn't reporting. Check the CloudWatch console to verify the
LoadBalancer is still publishing the HTTPCode_ELB_5XX_Count metric.

If the ALB was replaced, you may need to update the alarm's
LoadBalancer dimension to the new ALB ARN.

You can delete and recreate the alarm with the new dimensions using
the AWS CLI.
