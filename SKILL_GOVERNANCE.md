# Skill Governance — precise invocation readiness

*Audit against the `@skills` protocol (atskills.one / SylphAI-Inc/atskills, SKILLS.md spec), 2026-08-25.*

## Audit result: 8/9 PASS, 1 mitigated

| # | Protocol rule | Result |
|---|---|---|
| 1 | Every skill = folder with SKILL.md (name + description) | ✅ 409/409 |
| 2 | Path identity; name unique | ✅ 0 collisions |
| 3 | Lowercase-kebab paths (gh: paths are case-sensitive) | ✅ 0 violations |
| 4 | Description = capability phrasing ("what + when to use") | ✅ 409/409 |
| 5 | §1.5: directory menus over 128 skills are refused | ⚠️ root `skills/` menu (409) IS refused — **mitigated** via `skills/skill-catalog` |
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
  tables map all 409 skills to exact paths + task types + one-line descriptions.
- Save/install a skill into a project: `atskills save gh:jhkchan/aws-agent-skills/skills/<name>`
  (writes `.atskills/<name>/` + `.source` provenance; `:install` appends to `.autotrigger`).

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

## Deprecation & versioning

- `metadata.lifecycle_status`: active | deprecated | retired (schema-enforced).
- `metadata.version` per skill (string). Quarterly freshness re-audit per MAINTENANCE.md.
