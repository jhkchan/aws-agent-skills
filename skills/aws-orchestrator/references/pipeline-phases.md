# Pipeline Phases — Reference

Routing-only reference for the 4-phase CloudOps audit pipeline. Loaded on
demand by the orchestrator when the user requests phase-level detail or
transitions between phases. This file ROUTES to specialists; it does not
teach specialist technique. Each phase lists only: (a) phase inputs,
(b) routing decisions, (c) exit criteria, (d) loop-back triggers.

## Why 4 phases mapped to CloudOps audit

The pipeline is anchored on the **detective-audit** wedge: skills that read AWS
configuration state and emit a deterministic VERDICT. The 3 specialist auditors
each own one service's verdict logic. Assess feeds resources to audit,
Prioritize ranks audit findings, Remediate fixes them.

| CloudOps phase | Pipeline stage | Skills invoked | Why split |
|---|---|---|---|
| Inventory & baseline | 1 Assess | (all, discovery mode) | Need to know what exists before auditing |
| Detective audit | 2 Audit | s3/iam/ec2 auditors | Each service has distinct config-shape and verdict logic |
| Finding ranking | 3 Prioritize | (orchestrator ranks) | Severity/cost/compliance ranking is cross-service, not specialist |
| Fix generation | 4 Remediate | (each auditor's remediation section) | Remediation is service-specific but ordered by priority |

## Phase Indicator Format

Every substantive orchestrator response emits a phase indicator:

```
[Phase: <Assess | Audit | Prioritize | Remediate> | Resources: <summary> | Skills routed: <comma-separated>]
```

Rules:
- If multiple skills are routed, list them comma-separated.
- If the phase is ambiguous, prefix with `~`: `[Phase: ~Audit | ...]`.
- Always emit the indicator at the START of the routing response.

## Phase 1: Assess

**Inputs:** account context (regions, accounts), service scope (S3, IAM, EC2),
existing inventory (if any).

**Routing decision:** route resource-discovery to each in-scope auditor skill
in discovery mode:
- `s3-public-access-auditor`: enumerate buckets, check BPA state at account level
- `iam-least-privilege-advisor`: enumerate roles/policies, flag wildcard usage
- `ec2-security-group-auditor`: enumerate security groups, flag 0.0.0.0/0 rules

The orchestrator does NOT define what constitutes a "public" bucket or an
"over-permissive" role — the specialist owns that classification.

**Exit criterion:** resource inventory exists in `cloudops_state.md`; coverage
gaps identified (services in scope but not yet audited); user confirms scope
for deep audit.

**Loop-back trigger:** new resources discovered during Audit phase — re-enter
Assess to add them to inventory before continuing.

## Phase 2: Audit

**Inputs:** resource inventory from Phase 1; per-resource configuration data
(BPA settings, bucket policies, IAM policy JSON, SG rules).

**Routing decision:** route each resource to its matching auditor:
- S3 buckets (BPA + policy + ACL) -> `s3-public-access-auditor` for VERDICT
- IAM policies (actions/resources/conditions) -> `iam-least-privilege-advisor` for VERDICT
- EC2 security groups (inbound rules) -> `ec2-security-group-auditor` for VERDICT

The orchestrator does NOT classify resources itself, evaluate condition
strength, or determine severity — the specialists own that.

**Exit criterion:** every in-scope resource has a VERDICT recorded in
`cloudops_state.md` with the citing rule number and severity classification.

**Loop-back trigger:** a VERDICT of AMBIGUOUS requires either deep-dive
(specialist re-evaluates with more context) or human judgment — flag and defer
to Prioritize if unresolved.

## Phase 3: Prioritize

**Inputs:** complete findings list from Phase 2 (each with VERDICT, severity,
remediation complexity).

**Routing decision:** the orchestrator ranks findings cross-service using:
- **CRITICAL:** write-open exposure (S3 PutObject to *, IAM PassRole/*, SG
  allowing inbound on admin ports from 0.0.0.0/0)
- **HIGH:** read-open exposure (S3 GetObject to *, IAM wildcard read actions,
  SG allowing inbound on data ports from 0.0.0.0/0)
- **MEDIUM:** ambiguous posture (restricted wildcard with weak condition,
  IAM with some wildcards but no escalation paths)
- **LOW:** defense-in-depth recommendations (SAFE verdict but BPA not enabled,
  clean IAM policy but could be tighter)

The orchestrator may also map findings to compliance frameworks — the
ec2-security-group-auditor already maps to CIS/PCI-DSS/NIST controls.

**Exit criterion:** prioritized finding list with clear severity labels and
recommended remediation order. User confirms which findings to remediate first.

**Loop-back trigger:** a CRITICAL finding discovered late in prioritization —
escalate immediately and route to Remediate without waiting for full ranking.

## Phase 4: Remediate

**Inputs:** prioritized finding list from Phase 3.

**Routing decision:** route remediation generation to each specialist's
remediation section:
- S3 findings -> `s3-public-access-auditor` remediation guidance (enable BPA,
  remove public policy, restrict ACL)
- IAM findings -> `iam-least-privilege-advisor` remediation guidance (scope
  actions, restrict resources, add conditions)
- EC2 findings -> `ec2-security-group-auditor` remediation guidance (restrict
  CIDR, remove rule, use managed prefix list)

The orchestrator enforces the **pre-flight safety check** protocol: backup
before modify, prefer additive over destructive changes, treat write-open as
incident-response.

**Exit criterion:** remediation applied; re-audit (loop to Phase 2) confirms
VERDICT changed to SAFE/RESTRICTED/LEAST_PRIVILEGE.

**Loop-back triggers:**
- Remediation broke application access -> loop to Audit (re-verify) then Assess
  (did we miss a dependency?).
- Remediation only partially fixed the issue -> loop to Audit (deep-dive the
  remaining exposure) then Remediate (targeted fix).

## Cross-phase: Refinement loops

| Signal | Loop back to | Reason |
|---|---|---|
| Remediation broke application access | Audit (re-verify) then Assess (missed dependency?) | The fix may have unintended blast radius |
| New resources discovered during audit | Assess (add to inventory) then Audit | Coverage gap — new resource needs a VERDICT |
| Finding is ambiguous (AMBIGUOUS verdict) | Audit (deep-dive) or Prioritize (defer to human) | Ambiguous findings need human judgment or more context |
| Compliance mandate changes | Prioritize (re-rank) then Remediate | New compliance requirement shifts priority order |
| Write-open exposure found at any phase | Remediate IMMEDIATELY (incident response) | Every second of write-open exposure is data-destruction risk |
