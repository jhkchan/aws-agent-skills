# Baseline (no-skill) response: object-ownership-acl-conflict

---

Some objects in the bucket are accessible and others are not, even
though the bucket policy allows access to all objects. This might be
an ACL issue on the individual objects.

Check the ACL on the denied objects. Since they were uploaded by a
different account, the bucket owner might not have access. You could
try changing the ACL on those objects to give the bucket owner full
control.
