# Baseline (no-skill) response: v1-pipeline-migration-manual

This file captures what a generic assistant produces WITHOUT the
cicd-pipeline-automator skill loaded.

---

To migrate your V1 pipeline to V2:

```bash
aws codepipeline update-pipeline --cli-input-json file://v2-pipeline.json
```

Update the pipeline JSON to set `pipelineType: "V2"` and add a
`triggers` configuration. You may also want to set
`pollForSourceChanges: false` since V2 uses event-driven triggers.

```json
{
  "pipeline": {
    "name": "legacy-github-v1-pipeline",
    "pipelineType": "V2",
    "triggers": [
      {
        "gitConfiguration": {
          "push": [{"branches": ["master"]}]
        },
        "providerType": "CodeStarSourceConnection"
      }
    ]
  }
}
```
