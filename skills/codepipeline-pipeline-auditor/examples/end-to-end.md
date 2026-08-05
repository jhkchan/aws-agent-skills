# End-to-end usage scenario: codepipeline-pipeline-auditor

A walkthrough showing the skill auditing a production CodePipeline pipeline
that has both an unencrypted artifact store (NO_ENCRYPTION) and a deprecated
GitHub v1 source (CONFIG_GAP), demonstrating severity aggregation, the
artifact-exposure concept, and the CMK remediation workflow.

## Input (user prompt)

> Audit this CodePipeline pipeline before we go to production next week. It
> deploys a CloudFormation stack for our payment processing service.

```json
{
  "pipeline": {
    "name": "payment-service-prod",
    "roleArn": "arn:aws:iam::111111111111:role/service-role-AWS-CodePipeline-Service",
    "artifactStore": {
      "type": "S3",
      "location": "codepipeline-artifacts-payment-prod"
    },
    "stages": [
      {
        "name": "Source",
        "actions": [
          {
            "name": "GitHubSource",
            "actionTypeId": {
              "category": "Source",
              "owner": "ThirdParty",
              "provider": "GitHub",
              "version": "1"
            },
            "configuration": {
              "Owner": "fintech-org",
              "Repo": "payment-service",
              "Branch": "main",
              "OAuthToken": "{{resolve:secretsmanager:github-oauth:SecretString:token}}"
            },
            "outputArtifacts": [{"name": "SourceOutput"}]
          }
        ]
      },
      {
        "name": "Deploy",
        "actions": [
          {
            "name": "DeployCFN",
            "actionTypeId": {
              "category": "Deploy",
              "owner": "AWS",
              "provider": "CloudFormation",
              "version": "1"
            },
            "configuration": {
              "ActionMode": "CREATE_UPDATE",
              "StackName": "payment-service-prod",
              "RoleArn": "arn:aws:iam::111111111111:role/CFNDeployPayment",
              "TemplatePath": "SourceOutput::template.yaml"
            },
            "inputArtifacts": [{"name": "SourceOutput"}]
          }
        ]
      }
    ]
  }
}
```

Artifact bucket SSE: none.

## Expected output

```text
PIPELINE: payment-service-prod
VERDICT: NO_ENCRYPTION
REASON: Artifact store has no encryptionKey — pipeline artifacts (source code,
build outputs, templates) are stored without a customer-managed KMS key (Step 1).
Source also uses deprecated GitHub v1 OAuth credentials with no approval gate (Step 4/5).
FINDINGS:
  - [NO_ENCRYPTION] artifactStore.encryptionKey is absent; artifacts rely on bucket default SSE which is none — artifacts are UNENCRYPTED at rest (Step 1)
  - [CONFIG_GAP] Source action uses ThirdParty/GitHub (v1) — deprecated OAuth token model granting access to all repos under the authorizing user (Step 4)
  - [CONFIG_GAP] No ManualApproval action found despite a Deploy stage — production deploys without human verification (Step 5)
REMEDIATION:
  1. Create a customer-managed KMS key and add it to the artifact store:
     aws kms create-key --description "CodePipeline payment-prod artifact encryption"
     Then update the pipeline definition to include encryptionKey.id = <new-key-arn>.
  2. Grant the pipeline service role kms:Encrypt/kms:Decrypt/kms:GenerateDataKey on the new key.
  3. Migrate GitHub source to CodeStar Connection:
     aws codestar-connections create-connection --connection-type GH --name payment-prod-gh
     Update the source action owner to AWS, provider to CodeStarConnection.
  4. Add a ManualApproval stage with an SNS NotificationArn before the Deploy stage.
```

## Key reasoning demonstrated

- **Worst-finding aggregation:** the pipeline has three findings
  (NO_ENCRYPTION + two CONFIG_GAPs), but the verdict is NO_ENCRYPTION
  because it is the highest-severity category.
- **Artifact exposure concept:** the skill explains WHY unencrypted artifacts
  matter — they contain source code, templates, and build outputs that can
  be exfiltrated via S3 bucket access without ever touching KMS.
- **Deprecated source detection:** the ThirdParty/GitHub provider is flagged
  as CONFIG_GAP because it uses a persistent OAuth token with broad repo
  access, not just the scoped CodeStar Connection.
- **Missing approval heuristic:** the Deploy stage name triggers the
  production-pipeline heuristic, so the absent approval gate is flagged.
