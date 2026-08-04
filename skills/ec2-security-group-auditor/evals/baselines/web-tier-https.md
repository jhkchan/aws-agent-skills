# Baseline (no-skill) response: web-tier-https

This is the model output WITHOUT the ec2-security-group-auditor skill loaded.
It represents what a generic LLM produces when asked to audit the security group
without structured classification logic, compliance mapping, or the output format.

---

The security group has port 443 open to 0.0.0.0/0 which is normal for web
traffic, and SSH on port 22 from a private IP range. This looks fine for a
web server. You might want to make sure SSH is only from specific IPs.
