---
description: Audit Amazon Detective behavior graph coverage, member-account ingestion health, data-source package states, data freshness, GuardDuty integration, and Organizations delegated-admin posture.
nl_triggers:
  - "audit Detective behavior graph"
  - "is Detective enabled"
  - "Detective member accounts not ingesting"
  - "Detective data freshness check"
  - "GuardDuty Detective integration"
  - "Detective source graph coverage"
  - "Detective investigation readiness"
  - "check Detective Organizations admin"
  - "Detective data source packages"
  - "Detective coverage gap"
  - "Detective member invitation"
  - "behavior graph audit"
  - "Detective DETECTIVE_CORE stopped"
routes_to: detective-investigation-coverage-auditor
---

# /aws:audit-detective-investigation-coverage

Activate the `detective-investigation-coverage-auditor` skill and audit one
or more Amazon Detective behavior graph configurations for investigation
readiness.

## What it does

Reads a Detective configuration snapshot (graph ARN, member list,
data-source package states, lastDataReceived timestamps, GuardDuty detector
status, Organizations delegated-admin config) and applies the ordered
classification logic:

1. Graph existence — no behavior graph in the target region is NO_GRAPH
   (zero investigation capability).
2. Member ingestion — INVITED/ACCEPTED_BUT_DISABLED members or STOPPED
   DETECTIVE_CORE packages are INCOMPLETE_INGESTION (blind spots).
3. Data freshness — lastDataReceived > 24h for any COLLECTING member is
   STALE_DATA (investigation graph does not reflect current state).
4. Configuration gaps — GuardDuty detector disabled or no Organizations
   delegated admin is CONFIG_GAP (missing security-signal layer or
   auto-enrollment).
5. Aggregation — all checks pass = OK (full investigation readiness).

Emits a deterministic VERDICT per behavior graph:

```text
GRAPH: <graph-arn>
VERDICT: NO_GRAPH | INCOMPLETE_INGESTION | STALE_DATA | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [<severity>] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

- Validating Detective investigation readiness before a security incident
- Checking member-account ingestion completeness after org expansion
- Auditing data freshness for stale ingestion pipelines
- Verifying GuardDuty integration for the security-signal layer
- Reviewing data-source package coverage (DETECTIVE_CORE, EKS_AUDIT)
- Confirming Organizations delegated-admin auto-enrollment posture

## Example

```text
You: /aws:audit-detective-investigation-coverage
     Check Detective coverage for us-east-1 — we have 8 org accounts and
     need to make sure all are ingesting before our next incident-response
     exercise.

[Skill audits the behavior graph, member states, data-source packages,
data freshness, and GuardDuty integration, emitting the verdict block.]

GRAPH: arn:aws:detective:us-east-1:111111111111:graph:abc123
VERDICT: INCOMPLETE_INGESTION
REASON: Graph exists but 3 of 7 member accounts are in INVITED state...
FINDINGS:
  - [HIGH] Member 222222222222 in INVITED state, invitation sent 45 days ago
  - [HIGH] Member 333333333333 in INVITED state, invitation sent 62 days ago — expired
  - [HIGH] Member 444444444444 DETECTIVE_CORE in STOPPED state
  - [OK] Graph ARN exists in us-east-1
  - [OK] GuardDuty detector enabled
REMEDIATION:
  1. Re-send invitations to expired/pending accounts...
  2. Re-enable DETECTIVE_CORE for 444444444444...
```
