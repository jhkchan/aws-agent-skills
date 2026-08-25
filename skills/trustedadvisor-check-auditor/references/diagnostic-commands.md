# Diagnostic Commands — Trusted Advisor Check Auditor

Pre-flight and diagnostic command listings moved out of the SKILL.md body. Loaded on demand.

## Live-account pre-flight checks (support tier gate)

1. Confirm the caller can invoke
   `aws support describe-trusted-advisor-checks --language en` — if this
   returns `SubscriptionRequiredException`, the account has Basic or
   Developer support and only ~7 checks are accessible. Surface this BEFORE
   the operator asks "why are only 7 checks showing."
2. Verify CloudTrail is logging `support:Describe*` and
   `support:Refresh*` API calls — TA audit activity is not logged by default
   in CloudTrail management events unless the CloudTrail is configured for
   read-event logging on the Support service.
3. If the account is in an Organization, check whether a delegated admin is
   configured: `aws trustedadvisor describe-organization`. Without a
   delegated admin, TA runs per-account and there is no org-level
   aggregation.
