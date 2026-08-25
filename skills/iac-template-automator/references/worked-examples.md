# Worked Examples — IaC Template Automator

Secondary worked example moved verbatim from SKILL.md. Loaded on demand.

## Worked example — MANUAL_STEP_REQUIRED (hardcoded secret)

```text
PATTERN: rds-aurora-secret-rotation
TOOL: cloudformation
VERDICT: MANUAL_STEP_REQUIRED
TEMPLATE: (not generated — gate failed)
VALIDATION:
  - [BLOCK] cfn-nag F3: IAM policy with Action: '*' on the rotation Lambda role
  - [BLOCK] cfn-nag W11: MasterUserPassword hardcoded as plaintext string
SECURITY:
  - [FAIL] Hardcoded secret in MasterUserPassword: "MyPassword123!"
  - [FAIL] IAM role RotationExecutionRole has Action: "*" on Resource: "*"
FINDINGS:
  - [CRITICAL] MasterUserPassword is a plaintext literal. CloudTrail records this
    value in the CreateStack event. Rotate immediately via update-stack.
  - [CRITICAL] RotationExecutionRole grants admin permissions — a compromised
    rotation Lambda can do anything in the account.
REMEDIATION:
  1. Replace MasterUserPassword with {{resolve:secretsmanager:DBSecret:SecretString:password}}
  2. Add AWS::SecretsManager::Secret with GenerateSecretString
  3. Scope RotationExecutionRole to rds:ModifyDBCluster + secretsmanager:GetSecretValue + secretsmanager:PutSecretValue
  4. Re-run cfn-nag — both findings should clear
```
