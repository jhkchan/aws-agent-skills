# Worked Examples — CloudFormation cfn-lint Operator

Load-on-demand secondary worked examples moved verbatim from SKILL.md.

## REVIEW_REQUIRED — cfn-nag CRITICAL findings

### Worked example — cfn-nag finds CRITICAL findings (REVIEW_REQUIRED)

```text
CFN_LINT: template.yaml → my-app-stack
VERDICT: REVIEW_REQUIRED
CHECKLIST:
  [✓] Template file: template.yaml
  [✓] cfn-lint: PASSED (0 errors, 1 warning)
  [✓] validate-template: PASSED
  [!] cfn-nag: CRITICAL FINDINGS (2) — F1: IAM policy with Resource "*" in role TaskExecutionRole; F1000: Security group ingress from 0.0.0.0/0 to port 22
  [✓] ChangeSet: Not created (blocked by cfn-nag findings)
  [✓] Drift detection: IN_SYNC
  [✓] Stack policy: Not set
VERIFICATION_COMMANDS:
  cfn-lint template.yaml
  cfn_nag_scan --input-path template.yaml
```
