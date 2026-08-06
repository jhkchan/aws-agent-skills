# Baseline (no-skill) response: bastion-ssh-open

This is the model output WITHOUT the ec2-security-group-auditor skill loaded.
It represents what a generic LLM produces when asked to audit the security group
without structured classification logic, compliance mapping, or the output format.

---

Having SSH open to 0.0.0.0/0 is generally not recommended. You should restrict
it to known IP addresses. Consider using a bastion host or VPN.
