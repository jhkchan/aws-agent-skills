# Baseline (no-skill) response: cdk-pipeline-with-blue-green-lambda-automated

This file captures what a generic assistant produces WITHOUT the
cicd-pipeline-automator skill loaded.

---

To create a CDK pipeline with blue/green Lambda deployment:

```typescript
import * as pipelines from 'aws-cdk-lib/pipelines';

const pipeline = new pipelines.CodePipeline(this, 'Pipeline', {
  pipelineName: 'cdk-lambda-bluegreen-pipeline',
  synth: new pipelines.CodeBuildStep('Synth', {
    input: pipelines.CodePipelineSource.connection('acme-org/service', 'main', {
      connectionArn: 'arn:aws:codestar-connections:...',
    }),
    commands: ['npm ci', 'npx cdk synth'],
  }),
});

const prodStage = pipeline.addStage(new ProdAppStage(this, 'Prod'));
```

For the blue/green deployment, configure CodeDeploy with canary
traffic shifting in the Lambda alias configuration.
