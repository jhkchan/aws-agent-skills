# Eval: port-probe-low

**Difficulty:** easy
**Branch:** Step 5 — reconnaissance, low impact (default numeric banding)

## Prompt

Triage this GuardDuty finding. Emit the standard VERDICT block (FINDING,
VERDICT, REASON, REMEDIATION).

```
Finding name: port-probe-low
Finding type: Recon:EC2/PortProbeUnprotectedPort
Severity: 2.0
Title: EC2 instance has an unprotected port probed
Description: An external IP probed port 8080 on an EC2 instance. The security group allows inbound on port 8080.
Resource type: EC2 Instance
Resource: i-0devtest4477 (development test instance)
Action type: PORT_PROBE
Source IP: 198.51.100.100 (external)
Port probed: 8080
Count: 3
Confidence: LOW
Context: Development instance, port 8080 open to 0.0.0.0/0 for testing.
No successful login detected.
```
