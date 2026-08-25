# Auto-Remediation Automator — Worked Examples

Secondary worked examples moved from SKILL.md. The primary worked example
(AUTOMATED, simple S3 public access remediation) remains in SKILL.md.


## Worked example — MANUAL_STEP_REQUIRED, custom runbook missing (moved from SKILL.md)

```text
REMEDIATION: sg-open-ingress-remediation
RULE: custom-sg-no-open-ingress
RESOURCE_TYPE: AWS::EC2::SecurityGroup
WORKFLOW:
  - Detection: Custom Lambda Config rule on AWS::EC2::SecurityGroup.
  - Runbook: NONE — no AWS-managed runbook exists for security-group ingress revocation.
  - Trigger: TBD (manual recommended; the fix is reversible but false-positive prone).
  - Safety gates: TBD.
  - Audit: TBD.
TRIGGER: MANUAL
SAFETY: NONE — workflow not yet built
AUDIT: NOT WIRED
VERDICT: MANUAL_STEP_REQUIRED
GAP: No managed SSM runbook for security-group revocation. Build and test Custom-RevokeOpenSecurityGroupIngress (template provided in Step 6) before wiring remediation. Verify the SSM execution role exists.
TEMPLATE: (custom SSM document — see Step 6)
```
