---
name: aws-orchestrator
description: Start here for any AWS CloudOps audit, security review, compliance check, or infrastructure assessment. Diagnoses the task and routes to the right specialist skill(s) across the 4-phase CloudOps pipeline (Assess, Audit, Prioritize, Remediate). Use whenever the user mentions S3, IAM, EC2, security groups, bucket policy, public access, least privilege, compliance, CIS, PCI-DSS, audit, exposure, remediation, hardening, or asks 'is this resource secure/public/compliant'. A bare AWS resource name plus any audit verb is a sufficient trigger. Use even if the user does not explicitly say 'pipeline' — 'check my S3 buckets', 'audit this IAM role', 'are my security groups open' are all triggers.
license: Apache-2.0
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'false'
  phase: '0'
  supports_pipeline: 'true'
  entry_point: 'true'
  family: Management
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, cloudops, orchestration, pipeline, routing, audit, security, compliance
  tags: aws, cloudops, orchestration, pipeline, routing, audit, security
  dependencies: s3-public-access-auditor, iam-least-privilege-advisor, ec2-security-group-auditor
---

## Natural Language Triggers

Activate this skill's workflow when the user says things like:

- "check my S3 buckets for public access"
- "audit this IAM policy for least privilege"
- "are my security groups exposed?"
- "review my AWS security posture"
- "is this resource compliant with CIS?"
- "scan for public exposure across my account"
- "what should I audit first?"
- "help me prioritize these security findings"
- "generate remediation commands for these findings"
- "full CloudOps audit across my infrastructure"
- A bare AWS resource name + any audit verb ("audit this bucket", "check this role", "review this SG")

These produce the SAME structured behavior as `/aws:pipeline` or `/aws:status`.
Slash commands are shortcuts — natural language works equally well.

## When to Use

- User mentions an AWS resource, service, security check, or compliance task.
- User needs to diagnose where they are in a CloudOps assessment and what to do next.
- Session needs phase tracking, multi-skill coordination, or assessment-state memory.
- User is unsure which auditor skill to use — this skill triages.

**When NOT to Use:** A single isolated audit where the specific skill handles it
directly (e.g., "is this one S3 bucket public?" -> `s3-public-access-auditor`
directly). Non-AWS tasks fall outside this suite.

## On First Touch

1. **Check assessment state** — if no `cloudops_state.md` exists in cwd, create
   one with: account context, current pipeline phase, resources under review,
   findings so far, and skill routing history.
2. **Identify phase** — map the user's request to one of:
   Assess / Audit / Prioritize / Remediate.
3. **Route to specialist(s)** — never duplicate specialist content; always hand
   off with a phase indicator.

## Phase Indicators (every substantive response)

```
[Phase: Audit | Resources: 12 S3 buckets, 5 IAM roles | Skills routed: s3-public-access-auditor, iam-least-privilege-advisor]
```

If multiple skills are routed, list them comma-separated. If the phase is
ambiguous, emit the best-guess phase with a `~` prefix:
`[Phase: ~Audit | Skills routed: s3-public-access-auditor]`.

## The CloudOps Pipeline (4 phases)

```
Assess         →     Audit          →     Prioritize       →     Remediate
   |                  |                     |                      |
   v                  v                     v                      v
inventory          detective              severity ranking         CLI commands
resource lists     auditors               cost-impact              IaC patches
coverage gaps      deterministic          compliance-mandate       runbook steps
baseline state     VERDICT output         risk-weighted            actionable fixes
```

The pipeline is anchored on the **detective-audit** wedge: skills that read AWS
configuration state and emit a deterministic VERDICT (SAFE/PUBLIC/AMBIGUOUS,
PASS/FAIL, OPEN/RESTRICTED). The other phases orbit this core — Assess feeds
resources to audit, Prioritize ranks audit findings, Remediate fixes them.

This is NOT a rigid waterfall — phases loop back. A Remediate-stage "the fix
broke production" routes back to Audit (re-verify) or Assess (did we miss a
resource?). The orchestrator provides the **skeleton**; the auditor provides the
**judgment**.

**MANDATORY READ** [`references/pipeline-phases.md`](references/pipeline-phases.md)
when first entering any phase, on phase transition, or when the user asks about
phase scope/exit criteria. **MANDATORY READ**
[`references/routing-logic.md`](references/routing-logic.md) — INCLUDING the
in-domain-no-match fallback section — when triaging an ambiguous query or
picking among multiple specialist candidates.

### Phase 1: Assess (Inventory & Baseline)
**Goal:** Enumerate what exists, identify coverage gaps, and baseline the
current state before any deep audit.

| Step | What | Specialist Skill |
|------|------|------------------|
| Resource inventory | List S3 buckets, IAM roles/policies, EC2 security groups | (all audit skills in discovery mode) |
| Coverage check | Which resources lack BPA, have wildcard policies, open SG rules | s3/iam/ec2 auditors (discovery pass) |
| Gap identification | Services not yet covered by a skill | (orchestrator: log as coverage gap) |

**Phase exit criterion:** resource inventory exists; coverage gaps identified;
user confirms scope for deep audit.

### Phase 2: Audit (Detective — the core wedge)
**Goal:** Read AWS configuration state and emit a deterministic VERDICT for
each resource. This is the strategic center of the pipeline.

| Step | What | Specialist Skill |
|------|------|------------------|
| S3 exposure audit | BPA, ACL, bucket policy -> PUBLIC/SAFE/AMBIGUOUS | s3-public-access-auditor |
| IAM policy audit | Wildcard actions/resources, escalation -> OVERPERMISSIVE/LEAST_PRIVILEGE/AMBIGUOUS | iam-least-privilege-advisor |
| EC2 SG audit | Inbound rules, 0.0.0.0/0 -> OPEN/PUBLIC_NONCRITICAL/RESTRICTED | ec2-security-group-auditor |

**Phase exit criterion:** every in-scope resource has a VERDICT; findings are
recorded in `cloudops_state.md` with severity classification.

### Phase 3: Prioritize (Rank Findings)
**Goal:** Rank audit findings by severity, cost-impact, and compliance-mandate
so remediation targets the highest-risk items first.

| Step | What | Specialist Skill |
|------|------|------------------|
| Severity ranking | CRITICAL (write-open, escalation) > HIGH (read-open) > MEDIUM (ambiguous) > LOW (defense-in-depth) | (orchestrator: rank by verdict + context) |
| Compliance mapping | Map findings to CIS/PCI-DSS/NIST controls | ec2-security-group-auditor (has compliance mapping) |
| Cost-impact | Quantify exposure (data breach risk, compliance penalty) | (orchestrator: annotate) |

**Phase exit criterion:** prioritized finding list with clear CRITICAL/HIGH/MEDIUM/LOW labels and remediation order.

### Phase 4: Remediate (Fix)
**Goal:** Generate specific, actionable remediation — CLI commands, IaC patches,
or runbook steps — for each prioritized finding.

| Step | What | Specialist Skill |
|------|------|------------------|
| Remediation commands | aws-cli commands with pre-flight backup | (each auditor's remediation section) |
| IaC patches | Terraform/CloudFormation snippets | (each auditor's references) |
| Verification | Re-run audit to confirm fix | (loop back to Phase 2) |

**Phase exit criterion:** remediation applied; re-audit confirms VERDICT changed from PUBLIC/OPEN/OVERPERMISSIVE to SAFE/RESTRICTED/LEAST_PRIVILEGE.

## Cross-phase: Refinement loops

Findings are not terminal — they loop back. The orchestrator's job is to
recognize the signal and pick the loop-back target.

| Signal | Loop back to | Reason |
|---|---|---|
| Remediation broke application access | Audit (re-verify) then Assess (did we miss a dependency?) | The fix may have unintended blast radius |
| New resources discovered during audit | Assess (add to inventory) then Audit | Coverage gap — new resource needs a VERDICT |
| Finding is ambiguous (AMBIGUOUS verdict) | Audit (deep-dive the condition) or Prioritize (defer) | Ambiguous findings need human judgment or more context |
| Compliance mandate changes | Prioritize (re-rank) then Remediate | New compliance requirement shifts priority order |

## Domain

AWS CloudOps / Security & Compliance Auditing.
