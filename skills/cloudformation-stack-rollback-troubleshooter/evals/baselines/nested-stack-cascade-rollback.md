# Baseline (no-skill) response: nested-stack-cascade-rollback

---

Your parent stack is stuck because of a nested stack failure. The
nested stack has a custom resource that timed out. Try running
continue-update-rollback on the parent stack to retry the rollback.

If that doesn't work, you may need to delete the parent stack and
recreate everything. The nested stack structure makes this complicated
so you might want to contact AWS support.
