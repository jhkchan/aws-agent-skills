# Pillar question bank and improvement plan patterns — deep reference

This reference expands the SKILL.md review procedure with the
canonical pillar question sets, risk-tier rationale templates,
improvement plan patterns, Prosperity pillar (2025) coverage,
full NEVER list, and edge-case handling. Load when answering
pillar questions, drafting improvement plans, or applying
specialty lenses.

## Pillar overview

| Pillar | ID | Question themes | Specialty lens |
|---|---|---|---|
| Operational Excellence | `operationalExcellence` | Org alignment, readiness, ops events, ops review | — |
| Security | `security` | Security foundations, IAM, detection, infrastructure protection, data protection, incident response | Security lens |
| Reliability | `reliability` | Foundations, change mgmt, failure mgmt, workload METRICS, resilience | — |
| Performance Efficiency | `performance` | Compute, storage, database, networking, trade-offs, review | — |
| Cost Optimization | `costOptimization` | Practice, consumption, resource selection, supply/demand, optimization | — |
| Sustainability | `sustainability` | Region selection, user behavior patterns, hardware patterns, data patterns, dev process | — |
| Prosperity (2025) | (via Prosperity lens) | Growth sustainability, customer-centric measures, value streams, business alignment | `wellarchitected-prosperity` |

## Operational Excellence — question themes

### ORG — Organization alignment

- **ORG1.A:** How do you determine your priorities?
  - `HIGH_ISSUE` if no formalized priorities; `MEDIUM_ISSUE`
    if ad-hoc; `NO_ISSUE` if documented and reviewed.
- **ORG2.A:** How do you structure your organization to support
  your business outcomes?
- **ORG3.A:** How does your organizational culture support your
  business outcomes?

### PREP — Workload readiness

- **PRE1.A:** How do you ensure that your workload is ready for
  production?
- **PRE2.A:** How do you reduce deployment risks?
  - `HIGH_ISSUE` if no automated rollback (manual canary only).

### OPS — Operation of the workload

- **OPS1.A:** How do you understand the health of your workload?
- **OPS2.A:** How do you respond to events in your workload?
- **OPS3.A:** How do you reduce defects, ease remediation, and
  improve flow?

## Security — question themes

### SEC — Security foundations

- **SEC1.A:** How do you securely operate your workload?
- **SEC2.A:** How do you manage identities for people and
  machines?
- **SEC3.A:** How do you protect your network?
- **SEC4.A:** How do you protect your compute resources?
- **SEC5.B:** How do you classify your data?
- **SEC6.B:** How do you manage your data?
- **SEC7.B:** How do you encrypt and transmit your data?
- **SEC8.C:** How do you implement application security?
- **SEC9.C:** How do you implement human auth?
- **SEC10.C:** How do you implement auth for machines?
- **SEC11.C:** How do you authorize people and machines?
- **SEC12.C:** How do you separate environments?
- **SEC13.C:** How do you protect data at rest?
- **SEC14.C:** How do you protect data in transit?

### Risk-tier rationale templates

| Choice pattern | Suggested risk tier | Rationale template |
|---|---|---|
| No MFA on root account | HIGH_ISSUE | "Root account lacks MFA per IAM hygiene SOP" |
| No automated rollback | HIGH_ISSUE | "No automated rollback — manual canary per APP-SVC rollback SOP" |
| No encryption at rest | HIGH_ISSUE | "DynamoDB tables unencrypted per data protection SOP" |
| Single-AZ deployment | MEDIUM_ISSUE | "Single-AZ deployment acceptable for PREPROD, HIGH for PROD" |
| No CloudTrail in account | HIGH_ISSUE | "No CloudTrail per audit SOP" |

## Reliability — question themes

### REL — Reliability foundations

- **REL1.A:** How do you manage quotas and service limits?
- **REL2.B:** How do you plan your network topology?
- **REL3.B:** How do you design your workload to withstand
  component failures?
- **REL4.B:** How do you design interactions for a distributed
  workload to prevent failures?
- **REL5.B:** How do you design interactions for a distributed
  workload to tolerate failures?
- **REL6.C:** How do you monitor workload resources?
- **REL7.C:** How do you design your workload to respond to
  events?
- **REL8.C:** How do you back up data?
- **REL9.C:** How do you ensure workload recovery?
- **REL10.C:** How do you test resilience?
- **REL11.C:** How do you plan for disaster recovery?

### Resilience testing

- **REL10.B:** "How do you test resilience?"
  - `HIGH_ISSUE` if no chaos/fault-injection testing.
  - Reference the AWS Fault Injection Service (FIS) runbook.

## Performance Efficiency — question themes

### PERF — Performance

- **PERF1.A:** How do you select your compute solution?
- **PERF2.A:** How do you select your storage solution?
- **PERF3.A:** How do you select your database solution?
- **PERF4.A:** How do you select your networking solution?
- **PERF5.A:** How do you instrument your workload?
- **PERF6.A:** How do you optimize compute?
- **PERF7.A:** How do you optimize storage?
- **PERF8.A:** How do you optimize database?
- **PERF9.A:** How do you optimize network?
- **PERF10.A:** How do you trade off for performance?

## Cost Optimization — question themes

### COST — Cost optimization

- **COST1.A:** How do you implement cloud financial protection?
- **COST2.A:** How do you govern usage?
- **COST3.A:** How do you monitor usage and cost?
- **COST4.A:** How do you decommission resources?
- **COST5.A:** How do you manage demand, and supply resources?
- **COST6.A:** How do you optimize resource pricing?
- **COST7.A:** How do you use managed services?
- **COST8.A:** How do you meet cost targets when you select
  resources?
- **COST9.A:** How do you plan for data transfer charges?
- **COST10.A:** How do you review your workload?

## Sustainability — question themes

### SUS — Sustainability

- **SUS1.A:** How do you select Regions to support sustainability
  goals?
- **SUS2.A:** How do you take advantage of user behavior
  patterns?
- **SUS3.A:** How do you maximize hardware utilization?
- **SUS4.A:** How do you use managed services?
- **SUS5.A:** How do you optimize your code and algorithms?
- **SUS6.A:** How do you optimize your data?
- **SUS7.A:** How do you optimize your network?
- **SUS8.A:** How do you use automation to deploy your workload?

## Prosperity pillar (2025)

The Prosperity pillar is delivered as a specialty lens
(`wellarchitected-prosperity`), not part of the default
Framework. Import the lens and associate with the workload
before answering Prosperity questions.

### PROS — Prosperity themes

- **PROS1.A:** How do you sustain customer and business growth
  over time?
  - Covers customer acquisition, retention, expansion,
    contraction, and churn.
- **PROS2.A:** How do you measure customer-centric outcomes?
  - Covers Net Revenue Retention (NRR), Customer Acquisition
    Cost (CAC), Customer Lifetime Value (CLV), and the
    LTV:CAC ratio.
- **PROS3.A:** How do you align value streams to business
  outcomes?
  - Covers value-stream mapping, flow efficiency, and the
    relationship between engineering throughput and revenue.
- **PROS4.A:** How do you balance short-term and long-term
  investments?
  - Covers innovation vs. exploitation, the 70/20/10 rule,
    and reinvestment in technical debt.
- **PROS5.A:** How do you measure the prosperity impact of
  your workload?
  - Covers the link between workload health (availability,
    latency, error rate) and revenue / customer satisfaction.

### Risk-tier rationale for Prosperity

| Choice pattern | Suggested risk tier | Rationale |
|---|---|---|
| No NRR tracking | MEDIUM_ISSUE | "No NRR telemetry per finance review" |
| No value-stream map | MEDIUM_ISSUE | "No value-stream mapping per product ops" |
| No LTV:CAC ratio | HIGH_ISSUE | "No LTV:CAC tracked per growth SOP" |
| No link between workload SLOs and revenue | HIGH_ISSUE | "No revenue-impact SLO per growth SOP" |

## Improvement plan patterns

### Pattern 1 — Remediation owner + target date

Every HIGH risk item should have a remediation owner and a
target date. The skill surfaces this as a follow-up:

```
Improvement plan item #14:
  Question: How do you ensure automated rollback?
  Risk: HIGH_ISSUE
  Rationale: No automated rollback — manual canary per APP-SVC rollback SOP
  Remediation owner: payments-platform@example.com
  Target date: 2026-09-30
  Lab reference: https://www.wellarchitectedlabs.com/operational-excellence/
```

### Pattern 2 — Lens-specific remediation

Specialty lenses surface their own improvement plan items. The
Security lens may flag an IAM gap that the base Framework does
not:

```
Improvement plan item #7 (Security lens):
  Question: How do you scope IAM permissions?
  Risk: HIGH_ISSUE
  Rationale: Wildcard policy on Lambda execution role
  Remediation owner: security@example.com
  Target date: 2026-08-31
```

### Pattern 3 — Cross-pillar remediation

Some items cross pillars. A single-AZ deployment is a
Reliability risk AND a Prosperity risk (revenue impact on
outage):

```
Improvement plan item #3:
  Cross-pillar: Reliability + Prosperity
  Question: How do you design for multi-AZ?
  Risk: HIGH_ISSUE (PROD), MEDIUM_ISSUE (PREPROD)
  Remediation owner: platform@example.com
```

## Well-Architected Labs references

| Pillar | Lab URL |
|---|---|
| Operational Excellence | https://www.wellarchitectedlabs.com/operational-excellence/ |
| Security | https://www.wellarchitectedlabs.com/security/ |
| Reliability | https://www.wellarchitectedlabs.com/reliability/ |
| Performance | https://www.wellarchitectedlabs.com/performance-efficiency/ |
| Cost Optimization | https://www.wellarchitectedlabs.com/cost-optimization/ |
| Sustainability | https://www.wellarchitectedlabs.com/sustainability/ |
| Prosperity | https://www.wellarchitectedlabs.com/prosperity/ |

## Full NEVER list

1. NEVER answer a question with a risk-tier without citing
   workload evidence. A bare `HIGH_ISSUE` with no rationale is
   rejected by the operator as invalid.
2. NEVER create a milestone before the review is complete. A
   milestone is a point-in-time snapshot; answer updates after
   the milestone do NOT back-propagate.
3. NEVER reference a specialty lens without first running
   `import-lens` AND `associate-lenses`. An un-imported lens
   produces `ResourceNotFoundException` at `update-answer`.
4. NEVER treat Trusted Advisor findings as auto-answers. TA is
   an evidence source; the operator must confirm the risk-tier.
5. NEVER omit a pillar from `--pillar-ids` at workload creation.
   A missing pillar produces an incomplete consolidated report.
6. NEVER use `--selected-choices` only without
   `--choice-updates`. The `choice-updates` map captures the
   reason code (`RISK_GUIDANCE`, `OUT_OF_SCOPE`,
   `ARCHITECTURE_DECISION`) — `selected-choices` alone does not
   persist rationale.
7. NEVER assume the Prosperity lens is in the account by
   default. It is a 2025 specialty lens — opt-in via
   `import-lens`.
8. NEVER share a workload cross-account without confirming the
   recipient accepts via `accept-workload-share`. The workload
   does NOT appear in the recipient account until accepted.
9. NEVER trust the consolidated report to surface ALL gaps. The
   report enumerates answered items only — unanswered questions
   appear as `UNANSWERED` in a separate section.
10. NEVER use a milestone name that already exists. Milestone
    names must be unique within a workload; reuse produces
    `ConflictException`.

## Edge-case handling (extended)

### Custom lens versioning

Custom lenses are versioned. `list-lenses` shows the version
associated with the workload. Updating a custom lens to a new
version requires `associate-lenses` with the new version alias.
Old answers may not map cleanly to new question IDs.

### Prosperity lens unavailable in Region

The Prosperity lens may not be available in all Regions. Verify
via `list-lenses --region <r>` before importing. If unavailable,
run the review in a Region where the lens is supported.

### TA check migration

Some TA checks have migrated to AWS Resilience Hub (reliability)
or Security Hub (security). The mapping changes over time;
verify via `describe-checks` before mapping findings.

### Consolidated report size limit

For workloads with many lenses, the PDF report can exceed the
API response limit. Filter by lens before generating:

```bash
aws wellarchitected get-consolidated-report \
  --workload-id <id> \
  --format PDF \
  --lens-alias wellarchitected \
  --region us-east-1
```

### Workload review owner change

`update-workload --review-owner <new>` changes the review
owner. The previous owner loses write access. Confirm the new
owner is a valid principal before applying.

### Answer revision history

The Well-Architected Tool does NOT retain answer revision
history — only the latest answer persists. Use milestones to
capture review-cycle snapshots. There is no native "diff"
between milestones; export both milestone reports and diff
externally.

## Prosperity pillar — practical guidance

The Prosperity pillar (2025) reframes Well-Architected reviews
around business outcomes. Practical integration:

1. **Identify the value stream** the workload supports (e.g.,
   checkout → revenue).
2. **Map workload SLOs to revenue impact** (e.g., checkout
   latency SLO breach = cart abandonment).
3. **Track NRR / CAC / LTV** as Prosperity metrics.
4. **Balance short-term vs. long-term** — innovation vs.
   technical debt reduction.
5. **Use Prosperity lens findings** alongside the base
   Framework for a holistic review.

The Prosperity pillar does NOT replace the base Framework — it
complements it. Run both lenses in the same review cycle.
