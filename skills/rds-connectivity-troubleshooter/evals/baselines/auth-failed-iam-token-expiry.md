# Baseline (no-skill) response: auth-failed-iam-token-expiry

---

The error "password authentication failed" means the password is wrong.
Since you're using IAM database auth, the IAM token might be expired or
the IAM policy might not have the right permissions. Check the IAM policy
for `rds-db:connect` permission.

You could also try resetting the master password or rotating the secret
in Secrets Manager. If the issue keeps happening after the first 50
connections, there may be a connection pool issue — try reducing the pool
size or restarting the app more frequently.
