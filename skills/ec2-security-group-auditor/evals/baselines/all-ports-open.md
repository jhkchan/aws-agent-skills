# Baseline (no-skill) response: all-ports-open

This is the model output WITHOUT the ec2-security-group-auditor skill loaded.
It represents what a generic LLM produces when asked to audit the security group
without structured classification logic, compliance mapping, or the output format.

---

Opening all TCP ports (0-65535) to 0.0.0.0/0 is very dangerous. This exposes
every service on the instance to the internet. You should close this and only
open the specific ports you need.
