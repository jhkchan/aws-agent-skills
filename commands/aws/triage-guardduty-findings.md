---
description: Triage Amazon GuardDuty findings into context-aware severity (CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE) with false-positive detection and per-verdict remediation.
nl_triggers:
  - "triage this guardduty finding"
  - "guardduty severity"
  - "is this guardduty finding a false positive"
  - "port sweep from scanner"
  - "tor ip caller"
  - "cryptocurrency client"
  - "ssh brute force"
  - "malicious ip caller"
  - "credential exfiltration"
  - "guardduty triage"
  - "archive this finding"
  - "suppression filter"
  - "finding severity classification"
  - "recon finding"
  - "anomalous behavior finding"
routes_to: guardduty-finding-severity-triage
---

# /aws:triage-guardduty-findings

Activate the `guardduty-finding-severity-triage` skill and classify one or
more GuardDuty findings into a context-aware triage severity.

## What it does

Reads a GuardDuty finding (JSON from `get-findings`, or pasted structured
text) and applies the 7-step classification logic in order:

1. Validate finding input (type, severity, resource present).
2. False-positive override — check 6 FP patterns (authorized scanner, LB
   health check, known-safe DNS, expected Tor on public service, AWS
   service-linked role, documented change window).
3. CRITICAL — active compromise (crypto mining, credential exfiltration
   outside AWS, confirmed C2, ransomware, data exfiltration, DDoS
   participant, host lost, defense-evasion key deletion).
4. HIGH — strong compromise indicator (malicious-IP API call, SSH/RDP
   brute force, backdoor user, privilege escalation, suspicious file).
5. MEDIUM — behavioral anomaly or unusual reconnaissance (anomalous
   console login, port sweep from unknown source, permission enumeration).
6. LOW — reconnaissance, low impact (port probe, DGA domain request).
7. Numeric severity fallback for unknown finding types, then context
   overlays (count-based escalation, resource criticality).

Emits a deterministic VERDICT per finding:

```text
FINDING: <finding-type>
VERDICT: CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE
REASON: <1-2 sentences citing the classification step and finding context>
REMEDIATION: <specific action, or "Archive — likely false positive (<pattern>)">
```

## When to invoke

Paste a GuardDuty finding and ask any of:

- "triage this GuardDuty finding"
- "is this finding a false positive?"
- "what severity is this GuardDuty alert?"
- "should I archive this finding?"
- "which of these findings should I investigate first?"

A bare finding-type string + any triage verb ("triage this finding",
"classify this GuardDuty alert") also routes here via the orchestrator.

## Inputs

- A GuardDuty finding — either the full JSON (from
  `aws guardduty get-findings`) or structured text with the key fields
  (finding type, severity, resource, action, source IP, context).
- Optional: resource tags, security-group details, and contextual notes
  (e.g., "this instance is our Nessus scanner") for false-positive
  detection.

## Outputs

- One VERDICT block per finding.
- For multi-finding triage, a resource-level WORST VERDICT aggregation.
- Specific remediation: IR steps for CRITICAL, investigation steps for
  HIGH/MEDIUM, monitoring guidance for LOW, and archival + suppression-
  filter instructions for LIKELY_FALSE_POSITIVE.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Prioritize specialist for GuardDuty findings).
- `references/` section in the SKILL.md for links to the GuardDuty
  finding-types reference, severity documentation, and MITRE ATT&CK matrix.
