# Baseline (no-skill) response: s3-readonly-scoped

This file captures what a generic assistant produces WITHOUT the
iam-least-privilege-advisor skill loaded.

---

This looks like a reasonable read-only policy. It allows `GetObject` and
`ListBucket` on a specific bucket (`app-data-prod`) and its contents, which is
a fairly tight scope. The actions are explicitly named and the resources are
specific ARNs.

You should be fine with this one. Maybe double-check that the bucket name is
correct and that the role is only attached to the intended principal.
