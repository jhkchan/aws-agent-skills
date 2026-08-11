# Baseline (no-skill) response: period-misalignment-standard-metric

---

Your alarm is in INSUFFICIENT_DATA. The CPUUtilization metric exists
on the dashboard, so the issue is probably with how the alarm is
configured. Check that the namespace AWS/EC2 and the metric name
CPUUtilization are spelled correctly, and that the InstanceId
dimension matches your EC2 instance.

If the configuration looks right, the alarm might need more time to
evaluate. Wait a few more periods and see if it transitions out of
INSUFFICIENT_DATA.
