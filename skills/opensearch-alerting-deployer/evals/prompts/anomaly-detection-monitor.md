# Eval: anomaly-detection-monitor

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — anomaly detection monitor, RCF detector running, anomaly_grade > 0.9 trigger, severity 2, Chime destination

## Prompt

Create an OpenSearch anomaly detection monitor named
latency-anomaly-monitor on cluster
https://search-prod.example.com. The anomaly detector
latency-detector-001 is already created and in running state.
Trigger when anomaly_grade > 0.9, severity 2. Action: notify
Chime destination ops-chime-webhook (already configured).
Schedule every 5 minutes. Tags: Environment=production,
Type=anomaly.
