# Baseline (no-skill) response: scp-deny-s3-actions

---

The sandbox-app role is getting Access Denied even though both the IAM
policy and bucket policy allow s3:GetObject. This is unusual. Check if
there are any Service Control Policies at the organization level that
might be blocking S3 access.

If there's an SCP denying S3 actions on the Sandbox OU, you'll need to
update or remove it. SCPs take precedence over IAM policies.
