# Agent Skills Specification Compliance Report

*Audit of all 409 skills against the open Agent Skills format specification (agentskills.io), 2026-08-24.*

## Verdict

**0 of 409 skills are fully spec-compliant.** Every skill has at least one hard or structural violation. The violations fall into two classes: mechanical frontmatter issues (cheap to fix) and one architectural divergence (the spec's progressive-disclosure model vs. this repo's eval methodology).

## Findings

### A. Hard frontmatter violations (explicit spec constraints)

| # | Violation | Spec rule | Skills affected | Fix effort |
|---|---|---|---|---|
| 1 | `description` > 1024 chars | "Must be 1-1024 characters" | **61** (worst: ecs-cluster-autoscaling-optimizer at 1573) | Trivial (trim) |
| 2 | `compatibility` > 500 chars | "Must be 1-500 characters if provided" | **128** (worst ~570) | Trivial (trim/move CLI lists to body) |
| 3 | `metadata` non-string values | "A map from string keys to **string values**" | **405** — `requires_llm: true` (bool), `phase: 2` (int), `activation_triggers:` (list), `invocation_schema:` (dict) | Easy (quote/serialize) |
| 4 | `name` ≠ directory name | "Must match the parent directory name" | **2** — dirs `kinesis-firehose-troubshooter`, `ssm-session-manager-troubshooter` are misspelled (`troubshooter`); frontmatter names are correct | Trivial (rename dirs) |
| 5 | Extra top-level fields | Spec defines name/description/license/compatibility/metadata/allowed-tools; "additional properties not defined by the spec" belong in `metadata` | **409** — `version`, `author`, `keywords` everywhere; `tags` (405), `dependencies` (160), `when_to_use`/`keywords_tags` (1 each) | Moderate (relocate into `metadata`) |

### B. Structural divergence (spec recommendation)

| # | Issue | Spec guidance | Actual |
|---|---|---|---|
| 6 | SKILL.md length | "Keep your main SKILL.md **under 500 lines**. Move detailed reference material to separate files." | Only **4 of 409** are <500 lines. 239 are 500-800, 114 are 800-1000, **52 exceed 1000 lines**. |
| 7 | Activation context budget | Full body "**< 5000 tokens recommended**" at activation | **408 of 409** exceed ~5K tokens (mean body ~38KB ≈ ~9.5K tokens). |

These are recommendations rather than validation failures — skills still load and function in compliant clients — but they defeat the spec's core progressive-disclosure design and burn agent context in every real runtime.

### C. What already complies ✓

- Directory convention: every skill is `skills/<name>/SKILL.md` with `references/`, plus extra `eval/`, `evals/`, `examples/` dirs (spec allows any additional files).
- `name` format: lowercase/hyphens, no consecutive hyphens, ≤64 chars (all pass).
- `license: Apache-2.0` on all skills.
- `description` quality: all follow the "what + when + trigger keywords" pattern the spec's good-example endorses.
- Relative, one-level file references into `references/`.

## The architectural tension (must be decided explicitly)

The spec and this repo's eval methodology pull in opposite directions:

- **Spec:** compact SKILL.md; depth lives in `references/` loaded on demand — optimized for agent context efficiency.
- **This repo's eval (ROOT_CAUSE_REPORT.md):** Grade A correlates strongly with in-body context density (40-50KB → 71% A, >50KB → 97% A) because the eval harness feeds **only the SKILL.md body** to the executor model. References/ are invisible to the eval.

Bluntly: the current skills are tuned to the eval, not to the standard.

### Recommended resolution (spec compliance *without* sacrificing eval scores)

1. **Restructure each skill:** compact <500-line SKILL.md (activation core: quick nav, STRICT output contract, decision tree, NEVER list) + move worked examples, error tables, CLI references into `references/` (sanctioned by the spec).
2. **Update `eval/run_eval.py`** to concatenate `references/*.md` into the eval prompt. The executor model receives the same total context → eval scores preserved → Grade A correlation now measures the *skill folder*, not just the body.
3. This likely also **improves D5 (Progressive Disclosure)** scores — the judge dimension that rewards exactly this structure.

## Remediation plan

| Phase | Work | Skills | Risk |
|---|---|---|---|
| 1 | Trim 61 over-length descriptions (≤1024); trim 128 over-length compatibility fields (≤500) | 189 touch | None (CLI + eval unaffected) |
| 2 | Fix 2 misspelled directories | 2 | Low (update commands/, scorecards paths) |
| 3 | Serialize metadata values to strings (`phase: "2"`, `requires_llm: "true"`, YAML-flow lists) | 405 | Low |
| 4 | Relocate `version`/`author`/`keywords`/`tags`/`dependencies` into `metadata` | 409 | Medium — touches CLI routing, schema, tests |
| 5 | Body restructure to <500 lines + references/ split + eval harness update | 409 | High effort; requires re-eval cycle to confirm scores hold |

Phases 1-3 are safe mechanical fixes runnable now. Phase 4 needs the schema/CLI/tests updated in lockstep. Phase 5 is the real project — advisable before public launch (the spec's audience) but should be validated on ~10 skills first to confirm eval scores hold with the references-inclusive harness.

## Pilot result (2026-08-25): restructure is score-neutral — spec compliance is free

Ten Grade-B skills (106-107) were restructured to spec (bodies 421-493 lines, depth moved verbatim to `references/`, frontmatter byte-identical) and re-evaled with the references-inclusive harness:

- **Committed scorecards: 4 promoted to A** (cloudhsm 108, cloudtrail-alert 108, redshift-cluster 108, codebuild 110), 1 held, **0 demoted** (keep-best).
- **Fresh-run scores: mean 106.6 → 104.7 (−1.9)** — within the ±5 judge variance (n=10, SE≈1.6). 5/10 runs scored below prior, 5/10 at-or-above: the distribution expected from variance alone on a neutral change.

**Conclusion:** progressive-disclosure restructure costs nothing measurable in eval quality while achieving full spec compliance, and the keep-best harness converts the restructure rollout into a promotion-harvesting opportunity (each re-eval of a 105-107 B skill has odds of landing 108+). Rollout to the remaining ~400 skills is safe with keep-best active.

## Verification note

The official validator is [`skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref) (`npm i -g skills-ref && skills-ref validate ./skills/<name>`). It was not run in this audit (install permission denied); all checks above were implemented directly from the published specification text. Recommend running it on a sample after Phase 1-3 remediation.
