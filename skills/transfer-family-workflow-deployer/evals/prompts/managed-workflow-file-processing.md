# Eval: managed-workflow-file-processing

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — managed workflow with COPY, TAG, CUSTOM Lambda steps, on-exception steps

## Prompt

Create a managed workflow for Transfer Family server s-abc123 in
us-east-1. The workflow should process incoming files: Step 1: COPY
from /file-landing-zone/incoming/ to /processed-data/landing/.
Step 2: TAG with Status=Processed. Step 3: CUSTOM Lambda
virus-scan-file. On-exception: TAG with Status=Failed and send SNS
notification. Attach the workflow to server s-abc123. S3 bucket:
file-landing-zone.
