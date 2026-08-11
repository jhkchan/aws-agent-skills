# Baseline (no-skill) response: war-answer-security-pillar-high-risk

This file captures what a generic assistant produces WITHOUT the
wellarchitected-review-operator skill loaded.

---

To answer security pillar questions, you can use the
`update-answer` CLI:

```
aws wellarchitected update-answer \
  --workload-id workload-abc123 \
  --lens-alias wellarchitected \
  --question-id <question-id> \
  --selected-choices <choice-id>
```

Mark the risky choice as high risk in the console. Make sure to
include notes about why.
