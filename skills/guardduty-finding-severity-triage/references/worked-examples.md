# Worked Examples — GuardDuty Finding Severity Triage

Secondary worked examples, moved verbatim from SKILL.md. Load on demand.

## Multi-finding aggregation example (moved from SKILL.md)

When triaging multiple findings for the same resource, the resource-level
verdict is the **worst** verdict across all findings:

```text
FINDING: Impact:EC2/CryptocurrencyClient!SSH
VERDICT: CRITICAL
REASON: Step 2 (active compromise) — confirmed crypto-mining client on EC2 instance i-0abc123. Numeric severity 8.0 escalated to CRITICAL because crypto mining confirms active compromise requiring immediate IR.
REMEDIATION: Isolate the instance immediately (Step: CRITICAL IR). Capture forensic state (EBS snapshot, memory dump) then quarantine the security group. Revoke the instance-profile credentials. Do NOT terminate — terminated instances lose volatile memory evidence.

FINDING: Recon:EC2/PortProbeUnprotectedPort
VERDICT: LOW
REASON: Step 5 (reconnaissance) — external port probe on port 3389. Internet background noise; no indication of successful access.
REMEDIATION: Monitor. Verify port 3389 should be open in the security group — if not needed, remove the inbound rule.

RESOURCE: i-0abc123
WORST VERDICT: CRITICAL (from CryptocurrencyClient finding)
```

