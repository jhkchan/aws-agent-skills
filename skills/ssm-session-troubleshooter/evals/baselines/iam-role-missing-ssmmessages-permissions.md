# Baseline (no-skill) response: iam-role-missing-ssmmessages-permissions

---

The session starts but then the data channel fails. This usually
means the instance role is missing permissions. Check that the role
has `AmazonSSMManagedInstanceCore` attached — it should include
everything Session Manager needs.

If you're using a custom role, you may need to add `ssm:*` or the
specific `ssmmessages` actions manually. The error in the agent log
(`ssmmessages:OpenDataChannel`) points to that being the issue.
