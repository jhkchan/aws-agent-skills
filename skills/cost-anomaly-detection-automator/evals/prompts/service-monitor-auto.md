# Eval prompt: service-monitor-auto

Design an automated cost anomaly detection pipeline for the following
requirement. Emit the standard ANOMALY block (MONITOR, SUBSCRIPTION,
ROUTING, REMEDIATION, AUDIT, VERDICT, TEMPLATE).

Design reference: service-monitor-auto
Account: 111111111111
Region: us-east-1

Requirement: alert on EC2 spend spikes.
Monitor type: DIMENSION (SERVICE=Amazon Elastic Compute Cloud - Compute)
SNS topic: arn:aws:sns:us-east-1:111111111111:critical-cost-alerts
Threshold: 50% deviation, IMMEDIATE frequency.
Pre-prod validation: completed (synthetic spike confirmed in 18 hours).

Include the monitor creation CLI, subscription wiring, and the SNS topic
policy entry for events.costanomaly.amazonaws.com.
