# Diagnostic Commands — ses-email-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Pre-flight safety checks (run before any SES CLI)

- **Confirm the account is out of sandbox:** `aws sesv2
  get-account` (`EnforcementStatus` = `PRODUCTION`).
- **Confirm domain ownership / DNS access:** `aws route53
  list-hosted-zones`. DKIM, MAIL FROM, DMARC must be publishable.
- **Confirm the dedicated IP quota:** `aws service-quotas
  get-service-quota --service-code ses --quota-code L-1BCE5A11`.
- **Confirm the SNS topic exists for bounce / complaint:** `aws
  sns list-topics`. Create one if missing (sns-topic-deployer).
- **Confirm IAM permissions:** caller needs
  `sesv2:CreateEmailIdentity`,
  `sesv2:CreateConfigurationSet`,
  `sesv2:CreateDedicatedIpPool`,
  `sesv2:CreateEmailTemplate`,
  `route53:ChangeResourceRecordSets`.
- **Confirm VPC settings (if VPC endpoint desired):**
  `enableDnsHostnames` and `enableDnsSupport` must both be `true`.

