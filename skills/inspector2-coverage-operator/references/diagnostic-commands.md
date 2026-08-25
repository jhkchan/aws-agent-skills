# Diagnostic commands — inspector2-coverage-operator

Live-account pre-flight command listings, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Live-account pre-flight commands (moved from SKILL.md)

**Live-account pre-flight (skip if offline plan):**
1. `inspector2 describe-organization-configuration` — capture
   `autoEnable.ec2/ecr/lambda`, `maxAccountLimitReached`.
2. `inspector2 list-delegated-admin-accounts` — capture delegated
   admin account ID(s).
3. `inspector2 list-members --only-associated` — capture members
   with `relationshipStatus: ENABLED`.
4. `inspector2 list-coverage` — coverage report per region.
5. `ec2 describe-instances --filters "Name=instance-state-name,Values=running"`
   — running instances for EC2 gap analysis.
6. `ssm describe-instance-information` — SSM agent `PingStatus:
  Online` (deep inspection requires online SSM).
7. `ecr describe-repositories` + `ecr put-image-scanning-configuration`
   — rescan-on-push state per repository.
8. `lambda list-functions` — runtime for Lambda scan eligibility.
