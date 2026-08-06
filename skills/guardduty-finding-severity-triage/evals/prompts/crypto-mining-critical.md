# Eval: crypto-mining-critical

**Difficulty:** medium
**Branch:** Step 2 — active compromise (threat-category escalation to CRITICAL)

## Prompt

Triage this GuardDuty finding. Emit the standard VERDICT block (FINDING,
VERDICT, REASON, REMEDIATION).

```
Finding name: crypto-mining-critical
Finding type: Impact:EC2/CryptocurrencyClient!SSH
Severity: 8.0
Title: Cryptocurrency Miner on EC2 instance
Description: GuardDuty detected an EC2 instance communicating with a known cryptocurrency mining pool.
Resource type: EC2 Instance
Resource: i-0abc123def456 (production-web-server)
Action type: NETWORK_CONNECTION
Destination IP: 198.51.100.42 (known mining pool: xmr.pool.minero.net)
Count: 12
Confidence: HIGH
Context: Production web server, no known maintenance window
```
