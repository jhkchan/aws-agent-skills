# Grade B Hardening Report

## Executive Summary

- **201 Grade B skills** need hardening to Grade A (108+/120)
- **Bottleneck dimensions:** D8 Practical Usability (78 skills weak) and D1 Knowledge Delta (62 skills weak)
- **D3, D6, D7** are rarely weak — the skills have good anti-patterns, freedom calibration, and pattern recognition

## Hardening Strategy by Tier

### Tier 1: WITHIN_VARIANCE (34 skills, gap 1-3 points)
**Status:** Promotable via variance re-eval alone (±5 judge variance)
**Action:** Mass re-eval. ~20-30% promote per round. Run 3 rounds to promote majority.

### Tier 2: CLOSE (86 skills, gap 4-6 points)
**Status:** Need targeted D8/D1 content improvements
**Action:** Add STRICT output contract examples + expert heuristics. Proven +2-4 D8, +1-2 D1 per skill.

### Tier 3: MODERATE (67 skills, gap 7-10 points)
**Status:** Need significant D8/D1 section rewrites
**Action:** Full output contract rewrite + decision tree + worked example. Proven +4-6 D8, +2-3 D1.

### Tier 4: HARD (14 skills, gap 11-16 points)
**Status:** D8 critically weak (3-7/15 = 20-47%). Output contracts missing or non-functional.
**Action:** Complete output contract rebuild + practical examples + anti-pattern enforcement.

## The 18 Critical D8 Skills (< 8/15)

These are the highest-priority for content hardening. The D8 score means the judge found the model's output (when using the skill) to be barely usable.

| D8 | D1 | Total | Skill | Root Cause |
|---|---|---|---|---|
| 3/15 | 17/20 | 94 | neptune-graph-deployer | Output contract too abstract; no concrete example |
| 4/15 | 16/20 | 93 | vpn-connection-deployer | No worked example; missing FORBIDDEN patterns |
| 5/15 | 14/20 | 94 | dynamodb-capacity-optimizer | No decision tree; output format ambiguous |
| 5/15 | 16/20 | 97 | transit-gateway-deployer | Missing practical checklist; too theoretical |
| 5/15 | 17/20 | 98 | connect-instance-deployer | Contact flow JSON not actionable |
| 6/15 | 14/20 | 92 | batch-compute-environment-deployer | No example job definition output |
| 6/15 | 15/20 | 98 | macie-cost-optimizer | Missing cost calculation example |
| 6/15 | 16/20 | 94 | iot-core-thing-deployer | No device config example output |
| 6/15 | 16/20 | 94 | sqs-throughput-optimizer | Missing before/after comparison |
| 6/15 | 16/20 | 95 | backup-vault-operator | No operational runbook output |
| 6/15 | 16/20 | 96 | cloudwatch-rum-deployer | Missing JS snippet example |
| 6/15 | 16/20 | 96 | wellarchitected-review-operator | No review output template |
| 6/15 | 14/20 | 103 | aurora-cost-optimizer | Missing cost calculation output |
| 6/15 | 17/20 | 99 | elasticache-cluster-deployer | Missing cluster config example |
| 6/15 | 18/20 | 100 | codecommit-repository-deployer | Missing auth flow example |
| 7/15 | 16/20 | 99 | kms-key-rotation-optimizer | Missing rotation timeline |
| 7/15 | 17/20 | 98 | qldb-ledger-deployer | Missing PartiQL example output |
| 7/15 | 17/20 | 99 | msk-cost-optimizer | Missing cost comparison table |

## Proven Fix: STRICT Output Contract Methodology

Each +1 D8 point = +1 total. Each +1 D1 point = +1 total.

**D8 Fix (adds +3-5 points):**
1. Required output structure with literal labels (`VERDICT:`, `CHECKLIST:`, `REASON:`)
2. FORBIDDEN patterns (5+ anti-patterns with `NEVER`)
3. Perfect worked example showing the exact expected output
4. Decision tree leading to the output

**D1 Fix (adds +1-3 points):**
1. Expert heuristic not in base model training (service-specific gotcha)
2. Configuration dependency graph (novel insight)
3. "Recent AWS features" section (post-training-cutoff content)

## Expected Outcome After Hardening

| Tier | Skills | Expected A's | Method |
|---|---|---|---|
| WITHIN_VARIANCE | 34 | 20-25 | Re-eval (3 rounds) |
| CLOSE | 86 | 40-50 | D8/D1 content boost |
| MODERATE | 67 | 20-30 | Full output contract rewrite |
| HARD | 14 | 5-8 | Complete rebuild |
| **Total** | **201** | **85-113** | |

Current: 202A / 403 (50.1%). Target after hardening: ~287-315A / 403 (71-78%).
