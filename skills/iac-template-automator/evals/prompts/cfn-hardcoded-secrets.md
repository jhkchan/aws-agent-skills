# Eval prompt: cfn-hardcoded-secrets

Validate this existing CloudFormation template. Emit the standard VERDICT
block (PATTERN, TOOL, VERDICT, TEMPLATE, VALIDATION, SECURITY, FINDINGS,
REMEDIATION).

Pattern: rds-aurora-secret-rotation
Tool: cloudformation

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: RDS Aurora with rotation
Resources:
  DBCluster:
    Type: AWS::RDS::DBCluster
    Properties:
      Engine: aurora-postgresql
      EngineVersion: "16.5"
      MasterUsername: appadmin
      MasterUserPassword: MyPassword123!  # HARDCODED
      DatabaseName: appdb
      StorageEncrypted: true
      DeletionProtection: true
  RotationRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: rotation-execution
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: '*'
                Resource: '*'
```

Expected: MANUAL_STEP_REQUIRED. The skill detects:
1. CRITICAL: MasterUserPassword is a hardcoded literal (visible in
   CloudTrail event payload).
2. CRITICAL: RotationRole has Action: '*' on Resource: '*' — the
   least-privilege baseline (rule 2) fails.
Both findings must appear in the output with specific remediation steps.
