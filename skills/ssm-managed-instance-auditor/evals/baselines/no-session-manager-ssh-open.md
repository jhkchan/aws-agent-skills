# Baseline (no-skill) response: no-session-manager-ssh-open

This instance (`i-0nossessionmanagersshopen`) is managed, patched, and
has fresh inventory — but its security group allows SSH (TCP/22) from
`0.0.0.0/0`, and there are no recent Session Manager sessions.

SSH open to the internet is a security risk. You should restrict the
security group rule to a known CIDR or remove it and use Session Manager
instead, which provides audited access without inbound ports.

Everything else about the instance looks healthy.
