# Baseline (no-skill) — missing-multi-account-coverage

> This is the response a model produces **without** the skill
> definition. It notes that not all accounts are enrolled but
> misses the effective coverage calculation (88/150 = 59%), the
> member status significance (PAUSED members are not being scanned),
> the ASDD auto-enable gap (new accounts won't be enrolled), and the
> PARTIALLY_CLASSIFIED verdict format. Generated for with-skill-vs-
> baseline comparison.

---

The Macie administrator account looks healthy but there are gaps in
multi-account coverage. Not all 150 organization accounts are
enrolled — only 95. You should invite the remaining accounts. Some
members may be paused or not yet accepted invitations.

```bash
aws macie2 list-members --region us-east-1
```
