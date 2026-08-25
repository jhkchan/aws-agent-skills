# Inspector2 Automation Automator — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Mindset — extended bullets

- **Detection** without **EventBridge routing** is a dashboard, not
  automation. The Inspector console shows findings; nobody looks
  unless paged.
- **Severity-based response** is the operational backbone:
  Critical findings get SSM-driven patching within hours; High gets
  Slack notification within a day; Medium/Low get queued for the
  next patch window. Treating all severities the same burns out the
  on-call.
- **Verification is the closing gate.** Inspector findings have a
  lifecycle (OPEN → SUPPRESSED or CLOSED). A patch that succeeds
  at the OS level but leaves the finding OPEN means the rescan
  never ran, or the finding is suppressed-but-not-resolved.

## Step 0: Expert knowledge — non-obvious Inspector behaviors

- **Inspector ECR scans run automatically on push when scanning is
  enabled.** A repo with `scanOnPush: true` scans each new image
  within minutes. A repo with `scanOnPush: false` requires manual
  `start-image-scan`. The default for new repos depends on account
  settings — verify per repo.

- **Inspector rescan for ECR is NOT automatic when new CVEs are
  published.** An image scanned at push-time is "scanned for life"
  unless explicitly rescanned. New CVE databases do NOT trigger
  re-evaluation. For production repos, schedule weekly rescans via
  EventBridge → Lambda → `start-image-scan`.

- **Inspector Lambda code scans run on function UPDATE, not
  continuously.** A function deployed with a vulnerable package
  stays "vulnerable" in Inspector until the function is updated
  with a patched version. New CVEs against the deployed version
  are detected on the next rescan cycle (Inspector rescans Lambda
  functions every few days automatically).

- **Inspector does NOT detect vulnerabilities in Lambda layers
  directly.** The layer's package is attributed to the function.
  A shared vulnerable layer triggers findings on every function
  that consumes it — useful for blast-radius analysis.

- **Inspector finding severity is NOT configurable.** Severity
  comes from the CVE database (CVSS score). A "Critical" CVE stays
  Critical regardless of business context. Use the
  `ResourceTag` filter or finding suppression to override triage
  for accepted-risk resources.

- **SSM patch baseline with `Operation: Scan` does NOT modify the
  instance.** It populates the SSM patch compliance dashboard. Use
  `Operation: Install` to apply patches. Wire Scan first
  (low-risk), then Install (state-changing).

- **Inspector → Security Hub integration is one-way.** Inspector
  forwards findings to Security Hub automatically when integration
  is enabled. Closing a finding in Inspector closes it in Security
  Hub (within ~5 minutes). Closing in Security Hub does NOT close
  in Inspector.

- **Inspector delegated admin requires an Organizational unit
  scope.** The delegated admin account manages Inspector for all
  member accounts in the Organization. Member accounts cannot
  disable Inspector or modify configurations.

- **Inspector findings have `Title`, `Description`, and `Remediation`
  fields.** The `Remediation.Recommendation.Text` field contains
  vendor-specific guidance (e.g., "Update package `openssl` to
  version 1.1.1n"). Parse this to drive the SSM Automation
  parameters dynamically.

- **`AWS-RunPatchBaseline` patches only packages in the approved
  patch baseline.** A CVE affecting a package NOT in the baseline
  (e.g., a third-party repo) is not patched by SSM. The CVE will
  re-appear in Inspector after rescan. Extend the patch baseline
  with the required source repository.

- **Inspector cannot scan an EC2 instance without SSM agent
  running.** Inspector relies on SSM for both scanning and patching.
  An instance without SSM agent appears in `list-coverage` as
  `NOT_DETECTED` — no findings will ever surface.

- **Container image rebuild requires CI/CD pipeline access.**
  Inspector detects the vulnerable image; CodeBuild (or equivalent)
  rebuilds it from a patched base image. The pipeline trigger is
  typically EventBridge → CodeBuild `start-build`.

## Recent AWS features (2024-2026)

- **Inspector Lambda code scans GA (2024):** Static analysis on
  Lambda deployment packages covering dependency CVEs. NOT runtime
  analysis. Limited to functions updated after Inspector Lambda
  coverage was enabled.

- **Inspector ECR automated re-scan (2024):** Inspector automatically
  rescans ECR images when the CVE database is updated (within 24
  hours of a new CVE publication). Previously required manual
  `start-image-scan`. Verify with `aws ecr describe-image-scan-findings`
  post-CVE release.

- **Inspector delegated admin enhancements (2024-2025):** Multi-account
  coverage reporting via `list-coverage` aggregated across all member
  accounts. Faster propagation of coverage changes (5-15 minutes).

- **Inspector finding aggregation in Security Hub (2025):** Improved
  finding correlation — Inspector findings now include
  `RelatedFindings` linking network reachability findings to
  CVE-based findings on the same instance.

- **Inspector Lambda runtime monitoring preview (2025-2026):**
  Limited preview of runtime behavior analysis for Lambda
  functions, complementing the static code scan. Check regional
  availability before designing workflows that depend on it.

- **SSM patch baseline integration with Inspector (2025):**
  `AWS-RunPatchBaseline` now reads Inspector finding metadata to
  prioritize patches. The patch document parameter
  `IncludeInspectorFindings: true` filters the patch operation to
  only Inspector-flagged packages.

## Expert heuristic — blast-radius scoping, validation protocol, CloudFormation pattern

**Concrete scoping techniques:**

| Technique | Mechanism | Blast-radius limit |
|---|---|---|
| Tag-based patch groups | `Patch Group: critical-prod-canary` tag | Restricts patch to canary instances |
| Non-prod OU promotion | Deploy in non-prod OU first, promote after soak | Zero prod exposure until validated |
| `Operation: Scan` before `Install` | SSM patch baseline mode | Validates baseline contents without state change |
| Rate-limit via SQS | EventBridge → SQS → Lambda → SSM | Caps concurrent patch executions |
| Maintenance window gate | Route Critical findings into the next window | Human gate per cycle |
| Snapshot gate | `aws:createImage` as first runbook step | Recovery path within minutes |

**Pre-production validation protocol (3-cycle rule):**

1. **Cycle 1 — SCAN-ONLY in non-prod:** Deploy Inspector + patch
   baseline in `Operation: Scan` mode. Monitor the SSM patch
   compliance dashboard for 1 week. Verify findings correlate with
   Inspector output.

2. **Cycle 2 — INSTALL in non-prod:** Promote baseline to `Install`.
   Plant a known-vulnerable instance. Verify the patch runs, the
   instance reboots, the Inspector finding transitions to CLOSED
   within 24 hours, and Security Hub reflects the closure.

3. **Cycle 3 — SCAN-ONLY in prod:** Deploy the validated baseline to
   production in `Operation: Scan` mode. Monitor for 1 week.
   Verify no false-positive patch compliance flags. Then promote
   to `Install` with snapshot gate enabled.

**CloudFormation scoping pattern (recommended for fleet rollout):**

```yaml
# Inspector-driven patching with snapshot gate and non-prod soak
Resources:
  PatchBaseline:
    Type: AWS::SSM::PatchBaseline
    Properties:
      Name: inspector-critical-patches
      OperatingSystem: AMAZON_LINUX_2
      ApprovalRules:
        PatchRules:
          - PatchFilterGroup:
              PatchFilters:
                - Key: CLASSIFICATION
                  Values: [Security]
                - Key: SEVERITY
                  Values: [Critical]
            ApproveAfterDays: 0
            ComplianceLevel: CRITICAL
      PatchGroups:
        - critical-patch-group

  PatchAutomationRunbook:
    Type: AWS::SSM::Document
    Properties:
      DocumentType: Automation
      Content:
        schemaVersion: '0.3'
        mainSteps:
          - name: Snapshot
            action: aws:createImage
            inputs:
              InstanceId: '{{ InstanceId }}'
              ImageName: 'pre-inspector-patch-{{ global:DATE_TIME }}'
              NoReboot: true
          - name: Patch
            action: aws:runCommand
            inputs:
              DocumentName: AWS-RunPatchBaseline
              InstanceIds: ['{{ InstanceId }}']
              Parameters:
                Operation: Install
                RebootOption: RebootIfNeeded

  EventBridgeRule:
    Type: AWS::Events::Rule
    Properties:
      Name: inspector-critical-auto-patch
      EventPattern:
        source: [aws.inspector2]
        detail-type: [Inspector Finding]
        detail:
          severity: [CRITICAL]
          status: [OPEN]
          resources:
            type: [AWS_EC2_INSTANCE]
      State: ENABLED  # Flip to ENABLED only after Cycle 2 validation
      Targets:
        - Arn: !Sub 'arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:automation-definition/AWS-RunPatchBaseline'
          RoleArn: !GetAtt EventBridgeInvokeSSMRole.Arn
```

**Detection of blast-radius breach post-deploy:** CloudWatch alarm on
`SSM > CommandInvocationCount > N in 5 minutes` (suggests a bad
EventBridge rule firing on a burst of findings). Also alarm on
`SSM > InstancePatchCompliance > NonCompliantCount > N` in 24 hours
(suggests a bad patch baseline applied account-wide). Both alarms
should page the on-call security team and trigger an EventBridge
rule that disables the Inspector auto-patch rule via
`aws events disable-rule`.
