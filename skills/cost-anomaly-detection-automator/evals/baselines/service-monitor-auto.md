# Baseline (no-skill) response: service-monitor-auto

This file captures what a generic assistant produces WITHOUT the
cost-anomaly-detection-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, pipeline template,
SNS policy, audit steps, expert Cost Anomaly Detection knowledge).

---

You can use AWS Cost Anomaly Detection to monitor EC2 spend. Create a
monitor in the Billing console or via the CLI. Point it at the EC2
service and set a threshold. When spend spikes, it will send an alert
to your SNS topic.

To create the monitor:

```
aws ce create-anomaly-monitor --anomaly-monitor ...
```

I don't remember the exact MonitorSpecification format. You might need
to check the AWS docs for the JSON structure. Once the monitor is
created, it should start detecting anomalies automatically.

Make sure your SNS topic exists and is subscribed to.
