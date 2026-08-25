# Diagnostic Commands — Well-Architected Workload Auditor

Load-on-demand command listings moved verbatim from SKILL.md: per-pillar risk enumeration, milestone trend analysis, account-wide sweep pagination, and share audit.

### Per-pillar risk enumeration
The `describe-workload` API returns aggregate `RiskCounts`. To produce the
`PILLAR_RISK` block in the output, iterate all six pillars:

```bash
for pillar in security reliability performance costOptimization operationalExcellence sustainability; do
  aws wellarchitected list-answers \
    --workload-id <id> --pillar-id $pillar \
    --query 'AnswerSummaries[*].Risk' --output text | sort | uniq -c
done
```

Each answer summary includes a `Risk` field (`HIGH_RISK`, `MEDIUM_RISK`,
`NO_RISK`, `NOT_APPLICABLE`, `UNANSWERED`). Aggregate these client-side to
produce per-pillar counts.

### Milestone trend analysis
Compare the `WorkloadSummary.RiskCounts` from the two most recent milestones:

```bash
aws wellarchitected get-milestone \
  --workload-id <id> --milestone-number <latest> \
  --query 'Milestone.WorkloadSummary.RiskCounts'
```

If HIGH_RISK decreased between milestones, remediation is progressing. If it
increased, the architecture is regressing — flag in REMEDIATION.

### Account-wide sweep (pagination)
```bash
aws wellarchitected list-workloads --max-results 50
# Drain NextToken:
aws wellarchitected list-workloads --max-results 50 --next-token <token>
```

For each workload, run `describe-workload` + `list-milestones`. The sweep
should flag STALE_REVIEW workloads first — these are the highest-priority
candidates for re-review. Process in batches of 10 workloads to avoid API
rate limits and keep output manageable.

### Share audit
```bash
aws wellarchitected list-workload-shares --workload-id <id>
```

Check `PermissionType` for each share. `CONTRIBUTOR` grants write access —
the shared principal can modify answers. Restrict to `READ` unless active
collaboration is intended.
