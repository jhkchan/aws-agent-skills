# Baseline (no-skill) response: config-gap-ssl-require-public

This file captures what a generic assistant produces WITHOUT the
dms-replication-task-auditor skill loaded.

---

This CDC task has the source MySQL endpoint using SslMode require, which
means SSL is enabled but the certificate is not verified. The target is
using verify-full which is better. The replication instance is set to
PubliclyAccessible true and is not Multi-AZ, which could be a risk.

You should consider making the instance private and enabling Multi-AZ for
high availability. The logging is enabled at warning level.

The SslMode require on the source provides encryption but not full
certificate validation.
