# Skill Freshness Maintenance

AWS launches features continuously. This repo's skills cover the **core audit surface** at authoring time, but without a refresh mechanism they go stale — and a stale "eval-backed" skill (Grade A on an outdated audit surface) is misleading. This document defines the **freshness cadence** that keeps skills current.

## Quarterly freshness re-audit (every 3 months)

### 1. Scan for recent features (week 1)

For each of the 12 CloudOps families, check what AWS launched in the last quarter:

- **AWS What's New feed:** https://aws.amazon.com/about-aws/whats-new/ (filter by the family's services)
- **AWS News Blog:** https://aws.amazon.com/blogs/aws/ (major feature announcements)
- **Per-service docs:** each service's "Release notes" or "What's new" page
- **AWS re:Post:** community-surfaced new features + gotchas

Focus on features that **change the audit surface**: new config fields, new security settings, new service capabilities, deprecated features, new quotas/limits. Ignore features that don't affect CloudOps auditing (e.g., SDK convenience features).

### 2. Update skills (week 2)

For each skill whose service had significant launches:

1. Read the current `SKILL.md`.
2. Add a **"Recent AWS features"** entry to the existing section (or update it) covering the new features + how they affect the audit.
3. If a feature **changes the classification logic** (e.g., a new config field that needs checking, a new security dimension), integrate it into the Process/classification steps — add the new check.
4. If a feature **deprecates** an existing check, mark it.
5. Keep the skill **lean**: only significant features a CloudOps auditor needs. Do NOT pad.

### 3. Re-evaluate (week 3)

After updating the skills, re-run the eval to confirm the updated content still scores Grade A:

```bash
aws sso login --profile default
python3 eval/run_eval.py --skill <updated-skill>   # per updated skill
# OR: python3 eval/run_eval.py                      # all skills (longer)
python3 eval/generate_readme_table.py               # refresh the README table
```

If a skill drops below Grade A after the freshness update (e.g., added content increased density → D5 dropped), apply the targeted feedback-driven fix (read the judge's cited defect, address it, re-eval).

### 4. Commit + tag (week 4)

```bash
git add -A
git commit -m "chore(freshness): Q<N> re-audit — <N> skills updated with recent features"
git tag freshness-Q<N>-<year>
git push origin main --tags
```

## What to watch for (high-velocity services)

These AWS services launch features most frequently — prioritize them each quarter:

| Family | High-velocity services | Watch for |
|---|---|---|
| Compute | Lambda, ECS, EKS | New runtimes, MicroVM, container features, access entries |
| AI/ML | Bedrock, SageMaker | Inference profiles, guardrails, new model access, endpoint types |
| Security | GuardDuty, Inspector2, WAFv2 | New detector types, runtime monitoring, new managed rules |
| Storage | S3, EBS, Backup | New storage classes, directory buckets, lifecycle features |
| Networking | CloudFront, Route53 | OAC updates, KeyValueStore, new routing policies |
| Governance | CloudTrail, Config, Organizations | Lake features, new resource types, SCP capabilities |
| Databases | RDS, DynamoDB | Blue/Green, Serverless v2, global tables, new engine versions |

## Contributor-driven freshness

Contributors can submit freshness PRs anytime (not just quarterly):

1. A contributor notices a new AWS feature that a skill doesn't cover.
2. They add the coverage (Recent AWS Features section + classification integration if needed).
3. They run `python3 eval/run_eval.py --skill <skill>` to confirm Grade A holds.
4. They open a PR. CI runs the assertion layer; the maintainer reviews + commits the LLM-judge scorecard.

This is the sustainable freshness model — the community surfaces new features faster than any single maintainer can.

## Freshness log

| Date | Quarter | Skills updated | Key features added | Commit |
|---|---|---|---|---|
| 2026-08-05 | Initial freshness pass | 71 (all) | Lambda MicroVM, Bedrock inference profiles, GuardDuty runtime monitoring, CloudTrail Lake, RDS Blue/Green, ECS Service Connect, S3 directory buckets, + more | (this commit) |

> **Add a row each quarter** so the freshness history is trackable.
