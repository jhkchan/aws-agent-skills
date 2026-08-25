# Error Handling (load on demand) — Amazon DataZone Domain Deployer

Failure-mode deep dives (zero-asset crawls, InvalidDomainExecutionRole,
PENDING subscriptions, SSO visibility, publish failures, cross-account
provisioning) moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)



### Data source crawl returns zero assets
- Cross-account IAM role trust policy is missing or incorrect. Verify
  the trust policy Principal is the full ARN of the DataZone domain's
  execution role. Verify the role has permissions on the S3 bucket /
  Redshift cluster / RDS instance.

### Domain creation fails with "InvalidDomainExecutionRole"
- The domain execution role does not exist or does not have the
  required permissions. Verify the role exists and has a trust policy
  allowing `datazone.amazonaws.com` to assume it.

### Subscriptions stuck in PENDING
- No approver has been configured for the project or the glossary
  term. Verify the project has an owner (who is the default approver).
  For glossary-term-routed approvals, verify the term has a designated
  approver.

### SSO users not visible in DataZone
- IAM Identity Center is not configured or the DataZone domain is not
  linked to the SSO directory. Verify SSO is enabled and the domain
  was created with SSO authentication enabled.

### Asset publishing fails
- The asset may be in DRAFT status or the project member may not have
  publish permissions. Verify the asset status and the user's project
  role (owner or member with publish permission).

### Cross-account subscription provisioning fails
- The consumer account does not have the required IAM role for
  receiving access. DataZone cross-account subscriptions may deploy a
  CloudFormation stack in the consumer account. Verify the consumer
  account has the necessary IAM permissions and service-linked roles.


