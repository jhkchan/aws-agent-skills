# Eval prompt: recon-portprobe-authorized-scanner

Diagnose the GuardDuty finding below. Walk the finding-type-driven
diagnostic tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, EVIDENCE, SUPPRESSION, REMEDIATION). The FINDING
line must reference the test-case id `recon-portprobe-authorized-scanner`.

Symptom: GuardDuty finding e5f6g7h8 in detector 12ab34cd (us-east-1).
Type `Recon:EC2/PortProbe`, severity 0.5 (Low). Recurring weekly for
the last 4 weeks; SOC asks whether to suppress.

```text
aws guardduty get-findings:
  service.action.portProbeAction.remoteIpDetails.ipAddressV4:
    "198.51.100.10"
  organization.asn: "AS19894"
  organization.org: "Qualys, Inc."
  location.country: "United States"
  portProbeDetail: scanned ports 1-1024 across 47 EC2 instances in
    prod VPC between 02:00-02:15 UTC Sunday

aws guardduty list-ip-sets:
  (empty — no trusted IP list configured)

Network team runbook documents 198.51.100.10/32 as the corporate
Qualys scanner CIDR (weekly vulnerability scan, Sunday 02:00 UTC).

VPC Flow Logs: only inbound SYN from 198.51.100.10 to multiple
instances on ports 22, 80, 443, 3306 — no established connections,
no outbound traffic from instances to 198.51.100.10.
```

Emit the standard diagnostic block.
