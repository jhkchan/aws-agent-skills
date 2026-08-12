# Baseline (no-skill) response: lifecycle-policy-first-match-delete

---

The image tag `v3` is no longer in the repository. It may have been
deleted by a lifecycle policy. Check your lifecycle rules and re-push
the image from your CI pipeline. You may want to increase the
`countNumber` on your retention rule to keep more images.

To prevent this in the future, consider adding a rule that keeps
images tagged with `prod-` for longer.
