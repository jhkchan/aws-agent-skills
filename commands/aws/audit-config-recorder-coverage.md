---
description: Audit AWS Config recorder coverage, delivery channel health, rules deployment, and conformance packs across one or more regions.
nl_triggers:
  - "audit AWS Config coverage"
  - "check Config recorder status"
  - "is Config recording all resources"
  - "Config delivery channel health"
  - "conformance pack deployment status"
  - "multi-region Config audit"
  - "Config rules coverage gap"
  - "includeGlobalResourceTypes"
  - "allSupported Config"
  - "Config recorder not recording"
  - "AWS Config setup audit"
  - "Config compliance posture"
  - "configuration recorder audit"
routes_to: config-recorder-coverage-auditor
---

# /aws:audit-config-recorder-coverage

Activate the `config-recorder-coverage-auditor` skill and audit AWS Config
posture across all four coverage layers for one or more regions.

## What it does

Reads AWS Config API responses (recorder config, recorder status, delivery
channel config, delivery channel status, config rules, conformance packs)
and applies ordered classification logic:

1. Recorder existence and status — no recorder or `lastStatus: FAILURE`
   is CONFIG_GAP (no recording at all).
2. Delivery channel health — no channel or `lastStatus: FAILURE` is
   DELIVERY_GAP (snapshots not delivered to S3).
3. Coverage scope — `allSupported: false` or no region with
   `includeGlobalResourceTypes: true` is INCOMPLETE_COVERAGE.
4. Rules and conformance packs — zero rules and zero packs is NO_RULES.
5. Aggregation — worst verdict wins (CONFIG_GAP > DELIVERY_GAP >
   INCOMPLETE_COVERAGE > NO_RULES > OK).

Emits a deterministic VERDICT per region:

```text
AUDIT: <audit-reference>
REGION: <region>
VERDICT: CONFIG_GAP | DELIVERY_GAP | INCOMPLETE_COVERAGE | NO_RULES | OK
REASON: <1-2 sentences citing the worst finding>
FINDINGS:
  - [CONFIG_GAP] <finding description (Step N)>
  - [DELIVERY_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste AWS Config API responses and ask any of:

- "audit my AWS Config coverage"
- "is Config recording all resource types?"
- "check delivery channel health"
- "are conformance packs deployed correctly?"
- "is Config healthy across all regions?"
- "why are Config rules showing stale compliance?"

A bare region name + any audit verb ("audit Config in us-east-1", "check
recorder coverage") also routes here via the orchestrator.

## Inputs

- AWS Config API responses from six describe-* calls per region:
  describe-configuration-recorders, describe-configuration-recorder-status,
  describe-delivery-channels, describe-delivery-channel-status,
  describe-config-rules, describe-conformance-packs.
- For multi-region audits: provide API responses for each region.
- Optionally: describe-configuration-aggregators output to distinguish
  local recording from aggregator-based cross-account visibility.

## Outputs

- One VERDICT block per region (multiple findings aggregate to the worst
  verdict).
- Enumerated FINDINGS list with per-finding layer and step citation.
- Specific remediation: create recorder, fix delivery channel, switch to
  allSupported, deploy rules/conformance packs.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Config governance and compliance coverage).
- `/aws:audit-securityhub-control-compliance` for Security Hub control
  compliance auditing.
