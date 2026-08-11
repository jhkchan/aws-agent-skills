# Eval: byoip-accelerator

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — BYOIP pool 203.0.113.0/24 in READY state, EC2 IP endpoint

## Prompt

Create a Global Accelerator using BYOIP pool 203.0.113.0/24 which
is already provisioned and advertised (READY state). Listener
TCP ports 80 and 443. Endpoint group in us-east-1 with traffic
dial 1.0. Endpoint: EC2 instance 10.0.1.10 with weight 128.
Health check TCP port 80, interval 10. Tags: Environment=prod,
IPType=byoip.
