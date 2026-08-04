---
description: Audit AWS Security Hub control compliance findings — classify each finding into a deterministic verdict (FAILED | WARNING | PASSED | NOT_APPLICABLE) and map to a specific fix action. Handles finding lifecycle states (suppressed, resolved, archived), NOT_AVAILABLE StatusReasons splitting, and multi-standard control families (FSBP, CIS, PCI-DSS, NIST 800-53).
nl_triggers:
  - "security hub compliance"
  - "control status"
  - "security hub finding"
  - "FSBP finding"
  - "CIS benchmark control"
  - "compliance verdict"
  - "security hub audit"
  - "suppressed finding"
  - "NOT_AVAILABLE status"
  - "StatusReasons"
  - "finding lifecycle"
  - "compliance gap report"
  - "remediation runbook mapping"
  - "PCI-DSS control"
  - "NIST 800-53 control"
  - "ASFF finding"
routes_to: securityhub-control-compliance-auditor
---

# /aws:audit-securityhub-control-compliance

Activate the `securityhub-control-compliance-auditor` skill and classify one
or more AWS Security Hub control findings into a deterministic compliance
verdict.

## What it does

Reads a Security Hub finding (ASFF JSON, pasted inline or read from file) and
applies the 8-step classification logic in declaration order:

1. Validate input and finding type (ASFF with Compliance block vs. integration
   finding).
2. RecordState = ARCHIVED -> NOT_APPLICABLE (stale, resource likely deleted).
3. Workflow.Status = SUPPRESSED + FAILED -> WARNING (suppressed failure —
   governance concern, not a pass).
4. Workflow.Status = RESOLVED + FAILED -> WARNING (pending re-evaluation;
   >48h escalate to FAILED).
5. Compliance.Status = NOT_AVAILABLE -> split by StatusReasons: NO_RESOURCES /
   DISABLED_CONTROL -> NOT_APPLICABLE; SUPPORTED_SERVICE_NOT_ENABLED /
   ASSESSMENT_FAILED / etc. -> WARNING.
6. Compliance.Status = FAILED -> FAILED (active non-compliance).
7. Compliance.Status = WARNING -> WARNING (partial compliance).
8. Compliance.Status = PASSED -> PASSED.

Emits a deterministic VERDICT per finding:

```text
CONTROL: <ControlId>
VERDICT: FAILED | WARNING | PASSED | NOT_APPLICABLE
REASON: <1-2 sentences citing the rule, specific field values, StatusReasons code>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>
REMEDIATION: <specific fix action from the control-to-fix-action table>
```

## When to invoke

Paste a Security Hub finding (ASFF JSON) and ask any of:

- "what's the compliance status of this finding?"
- "is this control failing or just suppressed?"
- "what's the fix action for this FSBP control?"
- "triage these Security Hub findings"
- "prepare a compliance gap summary"
- "this NOT_AVAILABLE finding — does it apply?"

A bare control ID + any audit verb ("audit S3.2", "check IAM.7") also routes
here via the orchestrator.

## Inputs

- A Security Hub finding in ASFF JSON (pasted inline or referenced by file
  path). Must include at minimum: `Compliance.Status`, `Workflow.Status`,
  `RecordState`, and ideally `Compliance.StatusReasons`, `Severity.Label`,
  `GeneratorId`, `Resources`, `UpdatedAt`, `FirstObservedAt`.
- Optional: multiple findings for aggregate verdict rollup.

## Outputs

- One VERDICT block per finding (multi-finding inputs aggregate to the worst
  verdict: FAILED > WARNING > PASSED > NOT_APPLICABLE).
- Specific remediation: CLI command from the control-to-fix-action mapping
  table, covering FSBP, CIS Benchmark, PCI-DSS, and NIST 800-53 control
  families.
- For NOT_AVAILABLE findings: the StatusReasons code that determines whether
  the verdict is NOT_APPLICABLE (NO_RESOURCES) or WARNING
  (SUPPORTED_SERVICE_NOT_ENABLED).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Security Hub compliance posture).
- `skills/securityhub-control-compliance-auditor/example/end-to-end-audit.md`
  for a full multi-finding walkthrough covering all four verdicts.
