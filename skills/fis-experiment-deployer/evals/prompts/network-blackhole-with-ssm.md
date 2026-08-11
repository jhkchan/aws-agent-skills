# Eval: network-blackhole-with-ssm

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SSM agent online, alarm OK, manual rollback documented

## Prompt

Create an FIS experiment "network-blackhole-app-to-db" in
us-east-1. Use SSM Run Command on app instance i-0abc456 (tagged
fis-target=true, SSM agent Online) to drop traffic from
10.0.0.20 (DB IP). Run for 5 minutes via SSM document
AWS-RunShellScript. Stop condition: alarm "fis-stop-api-latency"
(OK state, role has DescribeAlarms). Log to S3
"fis-logs-111111111111" + CloudWatch Logs
"/aws/fis/network-blackhole-app-to-db". budgetDuration 10 minutes.
