# Eval: missing-notification-plugin

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — operator requests SNS action but notification.yaml plugin is not configured on the domain

## Prompt

Create an OpenSearch cluster metrics monitor named
disk-usage-monitor on cluster
https://search-prod.example.com. Monitor disk usage and
trigger when it exceeds 80%, severity 1. Action: notify SNS
destination ops-alerts-sns. The notification plugin
      (notification.yaml) has NOT been configured on this domain.
Schedule every 5 minutes.
