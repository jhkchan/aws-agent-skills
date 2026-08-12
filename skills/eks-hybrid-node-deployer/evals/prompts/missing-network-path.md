# Eval: missing-network-path

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — no Direct Connect or VPN; on-prem servers cannot reach the EKS API endpoint (private endpoint only); nodes cannot register or maintain heartbeats

## Prompt

Register 2 on-prem servers as EKS hybrid nodes to cluster
prod-cluster in us-east-1. The on-prem data center does NOT have
Direct Connect or VPN configured. The servers have internet
access but cannot reach the EKS API endpoint (private endpoint
only). Hybrid node IAM role EKSHybridNodeRole.
