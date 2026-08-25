# Worked Examples — Tag Compliance Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Worked example — REVIEW_REQUIRED, manual Billing step

```text
COMPLIANCE: org-tag-compliance-partial
SCOPE: org root r-xxxx, all member accounts, us-east-1
POLICY:
  - Type: Organizations TagPolicy (baseline-compliance-tag-policy)
  - enforced_for: AWS::EC2::Instance, AWS::S3::Bucket
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances
  - Tag propagation: EC2 -> EBS only (ENI propagation missing)
PROPAGATION:
  - EC2 -> EBS: covered
  - EC2 -> ENI: NOT covered
COST:
  - Cost allocation tags: inactive
  - Activation method: BLOCKED — API returns AccessDeniedException (Billing console IAM access not enabled)
VERDICT: REVIEW_REQUIRED
GAP: Three blockers: (1) ENI tag propagation missing in auto-tagger Lambda; (2) cost allocation tag activation blocked — payer account administrator must enable "IAM User and Role Access to Billing Information" in the Billing console; (3) Config recorder scope excludes S3, so drift detection on S3 is blind.
TEMPLATE: (partial — see Steps 3, 5, 8 for the missing pieces)
```
