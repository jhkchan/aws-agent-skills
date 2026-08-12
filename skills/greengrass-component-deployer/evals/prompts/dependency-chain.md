# Eval: dependency-chain

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — component with HARD dependency (com.example.StreamCollector) and SOFT dependency (com.example.OptionalLogger), dependency resolution order noted

## Prompt

Create a Greengrass v2 component com.example.DataPipeline
version 2.0.0. It has a HARD dependency on
com.example.StreamCollector version 1.1.0 and a SOFT dependency
on com.example.OptionalLogger version 1.0.0. Deploy to thing
group PipelineDevices (10 devices) in us-east-1. The component
has an artifact at
s3://gg-artifacts/pipeline/2.0.0/pipeline.sh. Configuration
merge: batchSize=50. Tags: Environment=staging.
