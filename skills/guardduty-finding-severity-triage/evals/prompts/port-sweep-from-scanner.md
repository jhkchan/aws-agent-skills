# Eval: port-sweep-from-scanner

**Difficulty:** hard
**Branch:** Step 1 / FP-1 — authorized security scanner override

## Prompt

Triage this GuardDuty finding. Emit the standard VERDICT block (FINDING,
VERDICT, REASON, REMEDIATION).

```
Finding name: port-sweep-from-scanner
Finding type: Recon:EC2/PortSweepUnusual
Severity: 6.0
Title: Unusual port sweep by EC2 instance i-0scanner01
Description: GuardDuty detected an EC2 instance performing port sweeps against multiple targets.
Resource type: EC2 Instance
Resource: i-0scanner01 (tagged: security-scanner-nessus, Name: nessus-vuln-scanner)
Action type: PORT_SWEEP
Source IP: 10.0.5.20 (internal — approved pentest CIDR 10.0.5.0/24)
Ports swept: 22, 80, 443, 445, 3389, 1521, 3306, 5432, 6379, 8080, 8443
Count: 1
Confidence: MEDIUM
Context: Instance is tagged as the organization's Nessus vulnerability scanner.
CIDR 10.0.5.0/24 is documented as the approved pentest range.
```
