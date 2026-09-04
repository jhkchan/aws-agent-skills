# Error Handling — IAM Access Analyzer Finding Triage

Load-on-demand error-handling detail moved verbatim from SKILL.md.

## Step 0 — malformed `condition` object handling

- `condition` is `null` or not a dict (e.g., a string or array) → treat as
  absent condition `{}`. Note in output: "condition field malformed —
  treated as absent."
- `condition` contains non-string values (e.g., numbers) → evaluate the key
  name for strength classification; note the type anomaly.
- `condition` contains nested operators (`"StringEquals": {...}`) → flatten
  to key-value pairs for strength evaluation; note the operator if it is
  `StringLike` (weaker than `StringEquals`, see Delta 3).

## Step 0 — ERROR output for malformed or unparseable finding JSON

If `findingType` is missing or the finding JSON is unparseable, output:

```text
FINDING: <id or "unknown">
VERDICT: ERROR
REASON: Finding JSON is malformed or missing required fields — cannot triage.
REMEDIATION: Re-export the finding from aws accessanalyzer list-findings and verify the JSON structure.
```
