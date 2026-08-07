# Eval prompt: v1-pipeline-migration-manual

Migrate the following V1 pipeline to V2 and emit the standard VERDICT
block.

Operation: migrate-v2
Pipeline name: legacy-github-v1-pipeline

```json
{
  "ExistingPipeline": {
    "name": "legacy-github-v1-pipeline",
    "pipelineType": "V1",
    "stages[0].actions[0]": {
      "actionTypeId": {
        "category": "Source",
        "owner": "ThirdParty",
        "provider": "GitHub",
        "version": "1"
      },
      "configuration": {
        "Owner": "acme-org",
        "Repo": "legacy-service",
        "Branch": "master",
        "OAuthToken": "**** (stored in Secrets Manager)"
      },
      "outputArtifacts": ["SourceOutput"]
    }
  },
  "RequirementChecks": {
    "codestar-connections.list-connections": [],
    "source_provider_assessment": {
      "uses": "ThirdParty/GitHub (v1 OAuth)",
      "status": "DEPRECATED",
      "v2_compatible": false
    }
  }
}
```
