# Skill Governance — precise invocation readiness

*Audit against the `@skills` protocol (atskills.one / SylphAI-Inc/atskills, SKILLS.md spec), 2026-08-25. End-to-end verification against the reference CLI completed 2026-09-04 (below).*

## Audit result: 8/9 PASS, 1 mitigated

| # | Protocol rule | Result |
|---|---|---|
| 1 | Every skill = folder with SKILL.md (name + description) | ✅ 410/410 (incl. skill-catalog) |
| 2 | Path identity; name unique | ✅ 0 collisions |
| 3 | Lowercase-kebab paths (gh: paths are case-sensitive) | ✅ 0 violations |
| 4 | Description = capability phrasing ("what + when to use") | ✅ 410/410 |
| 5 | §1.5: directory menus over 128 skills are refused | ⚠️ root `skills/` menu (410) IS refused — **mitigated** via `skills/skill-catalog` |
| 6 | §6: bundled scripts confirm-by-change | ✅ 0 skills ship executable entry scripts |
| 7 | Search: capability-style phrasing | ✅ descriptions written as activation contracts |
| 8 | Cache-friendly: small fetch units | ✅ largest skill 193KB total, all under 200KB |
| 9 | No protocol-added fields required | ✅ protocol adds zero fields; agentskills.io frontmatter ⊇ requirements |

## How skills are called precisely

```
@skills:gh:jhkchan/aws-agent-skills/skills/<skill-name>
```

- Direct references resolve a single skill — always legal, regardless of the 128 rule.
- Agents unsure which skill to use should reference `skills/skill-catalog` first: 13 family
  tables map all 410 skills to exact paths + task types + one-line descriptions.
- Save/install a skill into a project: `atskills save gh:jhkchan/aws-agent-skills/skills/<name>`
  (writes the vendored copy to `.atskills/gh/jhkchan/aws-agent-skills/skills/<name>/` with a
  `.source` pin; make it auto-trigger by adding `@gh:jhkchan/aws-agent-skills/skills/<name>`
  to `.atskills/.autotrigger`).

## Why the root menu is refused (by design)

SKILLS.md §1.5 refuses menus >128 entries to protect context. Browsing
`gh:jhkchan/aws-agent-skills` (409 children) is therefore refused with guidance to narrow.
This is correct protocol behavior, not a defect. The catalog skill is the compliant
discovery surface. Family-level menus would also be legal (largest family = Security, 52),
but regrouping 409 directories would break every committed precise path — rejected.

## Governance invariants (enforced by tests)

1. `name` matches directory, lowercase-kebab, ≤64 chars (agentskills.io + menu identity).
2. `description` ≤1024 chars, non-empty, capability phrasing (activation contract).
3. Body <500 lines; depth in `references/` (progressive disclosure).
4. No executable entry scripts shipped (§6 safety trivially satisfied).
5. Eval-backed: co-located test-cases + committed median-of-3 scorecard per skill.

## End-to-end verification (reference CLI, 2026-09-04)

Ran the normative implementation (SylphAI-Inc/atskills `bin/atskills.js`, v0.1.0 from
source — the npm package `atskills` is not yet published, E404) against this repo:

| Check | Command | Result |
|---|---|---|
| Cloud resolution | `atskills get gh:jhkchan/aws-agent-skills/skills/s3-public-access-auditor` | ✅ fetches, caches (`~/.cache/atskills`), prints SKILL.md + full bundle (eval/, evals/, references/) |
| Catalog entry point | `atskills get …/skills/skill-catalog` | ✅ 87-line body; 13 `references/by-family/` tables listed |
| §1.5 refusal | `atskills get …/skills` and repo root | ✅ refuses ("holds 410 skills — over the 128") with a narrowing list — exactly as documented |
| Vendoring | `atskills save …/skills/vpc-peering-deployer` | ✅ copies to `.atskills/gh/…/`, `.source` pins revision `e3a1f4c` |
| Local-first after save | `atskills get gh:…/vpc-peering-deployer` | ✅ answers from the vendored copy, no network |
| Auto-trigger residency | `.autotrigger` line `@gh:…/vpc-peering-deployer` | ✅ `triggers` shows the skill `[saved]`; `prompt` injects name + description + path only |
| Unknown frontmatter fields | (throughout) | ✅ `license`, `compatibility`, `metadata.*` ignored per forward-compat rule — no rejections |

`.autotrigger` line grammar (verified): plain lines are **gitignore patterns** over
`.atskills/`; cloud lines are `@gh:owner/repo/path`; trailing `/` installs every skill
under a directory. Install = add a line, uninstall = remove it.

## Known trade-off: resident description size

The protocol's SKILLS.md suggests descriptions "under ~120 chars"; ours average 884
(median 932, max 1024 — all within the agentskills.io hard limit) ≈ **221 resident
tokens per skill**. The length is deliberate: the `Triggers:` keyword tails are the
activation signal for description-based runtimes (Claude Code, Cursor, Windsurf), and
D1/D8 eval scores reward precise activation contracts. Cost under `@skills` residency
scales with *installed* skills, not the repo: a project that auto-triggers 10 skills
 pays ~2.2K resident tokens. Guidance:

- **Discovery → install few**: browse `skills/skill-catalog` (one skill), `atskills save`
  or `@gh:`-line only the 3-10 skills a project actually uses.
- Never mass-install all 410 (`@gh:jhkchan/aws-agent-skills/` as an autotrigger line
  would also trip §1.5 — by design).

## Security audit (OWASP Agentic Skills Top 10 tooling, 2026-09-04)

Swept all 410 skills with the independent AST10 implementation
([jhkchan/owasp-ast10-agent-skills](https://github.com/jhkchan/owasp-ast10-agent-skills),
`audit` — 10 detector categories, 45 static checks per skill):

| Result | Count |
|---|---|
| ERROR-level findings (decided attack scenarios) | **0 / 410 skills** |
| Malicious payload / obfuscated exec / C2 / egress call sites | 0 (no bundled executable scripts ship at all) |
| Identity-artifact reads, SOUL.md/MEMORY.md persistence, config-file hijacking | 0 |
| Over-privilege grants (declared write/network/shell scope) | 0 declared — nothing to over-grant |
| Warning signals | 3 rules × 410 skills, all one root fact: no USF v1 `skill.usf.yaml` security manifest (content_hash / permissions / sandbox). USF v1 is a proposal; the tool itself notes this is "the normal state of a real package" |

Complementary scans: repo-wide regex sweep for live credential patterns found only
`AKIAIOSFODNN7EXAMPLE` (AWS's canonical documentation-example key) and a bare
`-----BEGIN RSA PRIVATE KEY-----` header — intentional fake fixtures inside eval
scenarios, not secrets.

**What a static sweep cannot decide** (the tool's own decidability ledger, honored here):
prose-level intent — typosquatting lookalikes (AST01-S01), prompt injection inside
instructions (AST01-S03, AST05-S05), fake "setup required" coercion (AST01-S04), and
malicious-intent-entirely-in-prose (AST08-S01/S03) — plus update drift (AST07) and
governance/process scenarios (AST09), which compare versions or live outside any one
package. For this repo that residual reduces to instruction text: every skill is
SKILL.md + references + eval fixtures, with zero executable entry scripts (§6 above).

## Deprecation & versioning

- `metadata.lifecycle_status`: active | deprecated | retired (schema-enforced).
- `metadata.version` per skill (string). Quarterly freshness re-audit per MAINTENANCE.md.
