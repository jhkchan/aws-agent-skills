# Baseline (no-skill) response: immediate-monitor-weekly-subscription

This file captures what a generic assistant produces WITHOUT the
ce-cost-anomaly-auditor skill loaded.

---

The account has an IMMEDIATE anomaly monitor with a WEEKLY subscription.
The monitor detects anomalies quickly but the subscription only sends
notifications weekly, so there may be a delay in hearing about cost
spikes. You might want to change the subscription frequency to IMMEDIATE
for faster alerting.

The threshold is set to $100 which is the default. For a $20,000/month
account this might generate some noise from normal fluctuations. RI and SP
coverage looks good at 82% and 75%. CUR is enabled.

Overall the setup is mostly fine, just consider adjusting the subscription
frequency and threshold.
