# Error Handling — GuardDuty Finding Severity Triage

Input-validation and malformed-finding edge cases, moved verbatim from SKILL.md. Load on demand.

## Malformed finding JSON handling (Step 0)

**Malformed finding JSON:** If the finding JSON is unparseable (truncated
`get-findings` output, missing closing braces, `null` fields where strings
are expected), output VERDICT: ERROR with REASON "finding JSON unparseable
— re-fetch the finding." Do NOT guess the finding type from a fragment —
a misread type leads to wrong severity classification. Specific edge
cases to handle:

- **`severity` as a string** (e.g., `"severity": "8.0"` instead of
  `"severity": 8.0`): some API proxies and export pipelines serialize
  numbers as strings. Parse it as a float before classification; do not
  error.
- **`resource` present but `resourceType` missing or null**: the finding
  has a resource block but no type identifier. Try to infer the type
  from the finding-type string's `ResourceType` segment (between `:` and
  `/`). If neither is available, output ERROR.
- **Finding type truncated** (e.g., `Impact:EC2/Crypto` instead of
  `Impact:EC2/CryptocurrencyClient`): do not pattern-match a partial
  type. Output ERROR — a truncated type means the finding was corrupted
  in transit.
- **`service.eventFirstSeen` / `eventLastSeen` missing**: skip the
  staleness check (Step 0) and proceed with classification. Note in
  REASON: "timestamps unavailable; staleness not assessed."
- **AWS partition mismatch** (GovCloud `us-gov`, China `cn-`): finding
  types are the same across partitions, but threat-intel IP lists and
  trusted-IP sets are partition-specific. If the finding is from GovCloud
  or China partition (check the finding ARN or account ID region prefix),
  note that FP-1/FP-2 IP-range checks may not apply — GovCloud uses
  different ELB health-checker IP ranges.

## Stale findings and finding-type naming convention (Step 0)

**Stale findings:** If `eventLastSeen` is more than 30 days in the past,
the finding is historical. GuardDuty retains findings for 90 days. Old
findings may reference resources that no longer exist (terminated
instances, deleted IAM users). Note the staleness in the REASON field
and check resource existence before recommending remediation:
`aws ec2 describe-instances --instance-ids <id>` or
`aws iam get-user --user-name <name>`.

Additionally, verify the finding type matches the GuardDuty naming
convention: `ThreatPurpose:ResourceType/ThreatFamilyName[.Variant][!DetectionMethod]`.
If the type does not parse (e.g., a raw string without the colon/slash
delimiter), flag it as ERROR — a malformed finding type means the detector
output is corrupt or the finding was hand-edited.

