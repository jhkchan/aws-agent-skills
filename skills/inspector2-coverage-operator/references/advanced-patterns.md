# Advanced patterns — inspector2-coverage-operator

Step-0 expert-knowledge deep dives and recent AWS features, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Step 0: Expert knowledge — non-obvious Inspector behaviors (moved from SKILL.md)

- **Org-mode enable is one-way for member accounts.** Once a member
  is associated (`relationshipStatus: ENABLED`), the member CANNOT
  self-disable; only the delegated admin can disassociate it.
- **Auto-enable only applies to NEW member accounts.** When the org
  is configured with `autoEnable`, existing members keep their
  pre-existing state. Audit each member via
  `batch-get-member-ec2-deep-inspection-state` and `list-members`.
- **EC2 deep inspection is opt-in on top of standard scanning.**
  Standard covers network reachability and OS-level CVEs; deep adds
  package inventory via the SSM association
  `AmazonInspector-ManageAWSAgent`. Instances opt out via
  `batch-update-ec2-deep-inspection-state`.
- **ECR rescan-on-push is configured at the repository.** Update
  ECR `put-image-scanning-configuration` with `scanOnPush: true`.
  `ecr-enhanced` pulls the Inspector agent for deep package
  inventory; `basic` uses the native ECR CVE list.
- **Lambda code vulnerability scanning requires runtime support.**
  Supported (2026): `python3.x`, `nodejs.x`, `java11/17/21`,
  `provided.al2023`. Unsupported (`dotnet`, `ruby`, `go` on
  `provided.al2`) are silently skipped. Inspector needs
  `lambda:GetLayerVersion` to scan layers.
- **SBOM export targets S3 with a KMS key.** Asynchronous:
  `start-sbom-export` returns a `reportId`; completion lands in the
  bucket. The bucket policy must grant `s3:PutObject` and KMS key
  must grant `kms:GenerateDataKey` to the Inspector service
  principal.
- **Coverage gap analysis is region-by-region.** A resource appears
  in `list-coverage` for the region scanned. Cross-region
  aggregation requires AWS Security Hub or a custom aggregator.
- **Inspector charges by scan per resource per region.** Disabling
  unused regions avoids cost. Surface expected cost in NOTES.
- **Delegated admin must be in the same Organizations root.** OU
  moves do not revoke delegation — disassociation requires explicit
  `disable-delegated-admin-account` from the management account.
- **Network reachability scans run from AWS.** Inspector analyzes
  Security Groups and route tables for internet exposure. Host-agent
  scanning (standard + deep) requires the Inspector agent via SSM.
- **Lambda scanning is per version, not per alias.** `$LATEST` is
  scanned; published versions scanned once. For continuous coverage,
  re-publish on changes.
- **ECR enhanced scan is rate-limited per repository.** Concurrent
  `start-image-scan` calls are serialized. Use `scanOnPush: true`
  rather than batched manual scans for high-volume registries.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Lambda code vulnerability scanning (2025)**: Inspector scans
  Lambda function code (Python, Node.js, Java) for CVEs in
  application dependencies; enabled via `enable --resource-types
  LAMBDA`. No separate flag is needed.
- **Inspector SBOM export (2024)**: export CycloneDX 1.5 or SPDX 2.3
  SBOM per account/region to a customer-owned S3 bucket with KMS
  encryption; `start-sbom-export` is asynchronous, status via
  `list-sbom-export`.
- **EC2 deep inspection (2024, refined 2025)**: package-level
  inventory scanning via the SSM association
  `AmazonInspector-ManageAWSAgent`; supports `packageNameFilters`.
  Instances opt in/out via `batch-update-ec2-deep-inspection-state`.
- **ECR enhanced scan (2024)**: deep package inventory beyond the
  native ECR CVE list; enabled via `ecr-enhanced` scan type.
- **Inspector for AWS Organizations (2023, refined 2024)**:
  delegated-admin model with `autoEnable` defaults; org-level
  member limit (default 1000 member accounts).
- **Inspector integration with AWS Security Hub (2025)**: findings
  auto-publish to Security Hub for cross-region and cross-account
  aggregation.
- **Inspector Network Reachability (2024)**: analyzes Security
  Group and route table state for internet exposure; no agent
  required.
