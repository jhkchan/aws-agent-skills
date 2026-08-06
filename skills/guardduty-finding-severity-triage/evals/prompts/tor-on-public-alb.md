# Eval: tor-on-public-alb

**Difficulty:** hard
**Branch:** Step 1 / FP-4 — expected Tor traffic on public-facing service

## Prompt

Triage this GuardDuty finding. Emit the standard VERDICT block (FINDING,
VERDICT, REASON, REMEDIATION).

```
Finding name: tor-on-public-alb
Finding type: UnauthorizedAccess:EC2/TorIPCaller
Severity: 5.0
Title: EC2 instance contacted by Tor exit node
Description: An EC2 instance was contacted by an IP address on the Tor exit node list.
Resource type: EC2 Instance
Resource: i-0albfrontend22 (Application Load Balancer managed instance, public-facing)
Action type: NETWORK_CONNECTION
Source IP: 185.220.101.45 (known Tor exit node)
Port: 443
Count: 8
Confidence: MEDIUM
Context: This EC2 instance is part of an ALB target group serving a public
whistleblower portal at tips.example.org. The service is intentionally
anonymous and Tor traffic is expected. No authentication is required.
```
