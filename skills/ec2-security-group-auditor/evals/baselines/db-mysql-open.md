# Baseline (no-skill) response: db-mysql-open

This is the model output WITHOUT the ec2-security-group-auditor skill loaded.
It represents what a generic LLM produces when asked to audit the security group
without structured classification logic, compliance mapping, or the output format.

---

MySQL port 3306 is open to the internet (0.0.0.0/0). This is a security risk.
You should restrict access to your application servers only. Consider using
security group references instead of CIDR blocks.
