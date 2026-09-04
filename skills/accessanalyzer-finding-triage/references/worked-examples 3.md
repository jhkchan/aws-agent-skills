# Worked Examples — IAM Access Analyzer Finding Triage

Load-on-demand worked examples moved verbatim from SKILL.md.

## Zone of trust — organization-scoped analyzer expected case (mini-example)

**Example — organization-scoped analyzer expected case:**
An org-scoped analyzer flags an S3 bucket policy granting `s3:PutObject` to
`arn:aws:iam::999999999999:root` where account 999999999999 is a member of
the same org. With an org analyzer, this would NOT be flagged at all. With
an account analyzer, it IS flagged but should be classified as EXPECTED
(intra-org CI/CD deployment account) with an archive rule.

## Organization-scoped analyzer example (intra-org cross-account)

```text
FINDING: s3-cross-account-org-member
RESOURCE: arn:aws:s3:::shared-data-lake
RESOURCE_TYPE: AWS::S3::Bucket
FINDING_TYPE: ExternalAccess
VERDICT: EXPECTED
RISK: LOW
REASON: Principal arn:aws:iam::999999999999:root (account 999999999999) is a member of the same AWS Organization as the resource owner account 123456789012. The account-scoped analyzer correctly flagged this as external to its zone of trust, but the principal is within the org governance boundary. The CI/CD deployment account 999999999999 is a documented data-lake consumer.
REMEDIATION: Create an archive rule on the account analyzer: filter on principal=arn:aws:iam::999999999999:root + resourceType=AWS::S3::Bucket. Document the integration owner and ticket reference. Alternatively, upgrade to an organization-scoped analyzer to eliminate these intra-org findings automatically.
```
