---
description: Diagnose an Amazon Inspector v2 finding (package CVE on EC2/ECR/Lambda, network reachability, Lambda code vulnerability) through a finding-type-driven diagnostic tree — classifies the finding, walks to the vulnerable artifact, emits ROOT_CAUSE_FOUND with the specific finding type and remediation path.
nl_triggers:
  - "inspector finding"
  - "inspector v2 finding"
  - "inspector2 finding"
  - "inspector CVE"
  - "inspector vulnerability"
  - "inspector package vulnerability"
  - "inspector network reachability"
  - "inspector code vulnerability"
  - "inspector lambda code scanning"
  - "inspector sbom export"
  - "inspector ecr image scan"
  - "inspector lambda layer scan"
  - "CVE on ec2 instance"
  - "CVE on ecr image"
  - "CVE on lambda function"
  - "inspector critical finding"
  - "inspector high finding"
  - "triage inspector finding"
  - "inspector false positive"
  - "inspector finding stale"
  - "inspector remediation"
  - "troubleshoot inspector"
routes_to: inspector2-finding-troubleshooter
---

# /aws:troubleshoot-inspector2-finding

Activate the `inspector2-finding-troubleshooter` skill and diagnose an
Amazon Inspector v2 finding through the finding-type-driven diagnostic
tree.

## What it does

Reads a finding description (finding ARN, finding JSON, CVE id, or a
resource ARN flagged by Inspector) plus the resource metadata, then
walks the finding-type-specific diagnostic tree to a root cause with
positive evidence:

1. **Pre-flight** — pull `batch-get-finding-details` (the single
   highest-signal command), verify Inspector coverage, check staleness
   via `lastObservedAt`. Short-circuits on missing context
   (NEED_MORE_INFO).
2. **Finding-type entry** — map the finding `Type` to a branch:
   - **PACKAGE_VULNERABILITY** → SSM inventory (EC2), ECR scan findings
     (ECR), Lambda layers + runtime (Lambda).
   - **NETWORK_REACHABILITY** → security group rules, route tables,
     public IP / IGW path.
   - **CODE_VULNERABILITY** → `batch-get-code-snippets` for the source
     line (Lambda code scanning).
3. **Layer-specific probes** — `list-inventory-entries`,
   `describe-image-scan-findings`, `get-function-configuration`,
   `describe-security-groups`, `describe-network-interfaces`,
   `list-sbom-export`, `batch-get-code-snippets`.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing probe that matches the
   finding), NEED_MORE_INFO (a probe requires operator input), or
   ESCALATE (AWS-side false positive or undocumented rule).

Emits a deterministic diagnostic block per target:

```text
TARGET: <resource-arn>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the finding type, vulnerable artifact,
  and failing probe>
FINDING_TYPE: <PACKAGE_VULNERABILITY | NETWORK_REACHABILITY |
               CODE_VULNERABILITY | UNKNOWN>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>
LAYER: <EC2_OS_PACKAGE | ECR_BASE_IMAGE | LAMBDA_LAYER |
        LAMBDA_DEPLOYMENT_PACKAGE | LAMBDA_RUNTIME |
        LAMBDA_SOURCE_DEFECT | SG_OVERLY_PERMISSIVE | SG_BROAD_CIDR |
        PUBLIC_IP_VIA_IGW | SBOM_SCOPE | NO_FIX_AVAILABLE |
        STALE_FINDING | STALE_IMAGE | UNKNOWN>
EVIDENCE:
  - <observed finding>
  - <failing probe — command and output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a finding description and ask any of:

- "Inspector fired a CRITICAL CVE on my EC2 instance"
- "Inspector Lambda code scanning found a hardcoded secret"
- "Network reachability finding on port 3306"
- "Inspector ECR image scan shows a vulnerable package"
- "Is this Inspector finding still actionable?"
- "Triage this Inspector finding"

A finding ARN or resource ARN + any finding type ("CVE-2024-5555 on
i-0abc123", "CODE_VULNERABILITY on checkout-handler") also routes here
via the orchestrator.

## Inputs

- Finding context: finding ARN, finding JSON (Type, Severity, Title,
  Description, Resources, PackageVulnerability / NetworkReachability /
  CodeVulnerability block), or CVE id + package name.
- Resource metadata: EC2 instance (SSM-managed status, platform, AMI),
  ECR image (repo, digest, tag), Lambda function (runtime, layers,
  handler), security groups, route tables.
- For live-account diagnosis: finding ARN, resource ARN, time window of
  the finding's last observation. The skill uses `batch-get-finding-details`,
  `list-coverage`, `list-inventory-entries`,
  `describe-image-scan-findings`, `get-function-configuration`,
  `describe-security-groups`, `describe-network-interfaces`,
  `list-sbom-export`, `batch-get-code-snippets`.

## Outputs

- One diagnostic block per finding / resource.
- FINDING_TYPE and LAYER values from the enumerated sets.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: SSM Run Command (EC2 patch), image rebuild
  (ECR), layer update or code fix (Lambda), SG restrict (reachability),
  finding suppression (false positive), or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Inspector v2 findings).
- `/aws:audit-securityhub-findings` for cross-service security posture
  audits (Security Hub aggregates Inspector findings).
- `/aws:troubleshoot-alb-5xx` for WAF blocks that may correlate with
  reachability findings.
