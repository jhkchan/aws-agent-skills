# Error Handling — SageMaker Pipeline Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


## Pipeline failure deep dives

### Pipeline creation fails with `ValidationException: Cycle detected`
- A circular dependency exists in the step edges. Inspect every
  `DependsOn` and property reference. Common cause: an upstream step
  references a downstream step's property.

### Execution fails with `iam:PassRole` error on first job
- The pipeline execution role lacks permission to pass the child-job
  role. Add `iam:PassRole` on the child role ARN to the pipeline role.

### ConditionStep errors with `Unable to resolve JsonGet`
- The property file was not produced. Verify the upstream step writes a
  `PropertyFile` with the expected name and the `json_path` matches.

### Caching re-runs steps unexpectedly
- The cache key changed. Common cause: image referenced by `:latest`
  whose content changed but tag did not; S3 input ETag changed;
  hyperparameter drifted. Pin images to digests and parameterize
  values you intend to sweep.

### RegisterModel creates versions but never deploys
- RegisterModel is the gate, not the deployer. Approval is a separate
  `UpdateModelPackage(ApprovalStatus=Approved)` call. CI/CD must poll
  or be EventBridge-triggered on approval, then deploy.

### EventBridge rule fires but pipeline never executes
- The target's invoke role lacks `sagemaker:StartPipelineExecution` or
  its trust policy doesn't allow `events.amazonaws.com`.

### ParallelismConfiguration=5 but steps still serialize
- The account quota caps total concurrency across ALL pipelines. Check
  `aws service-quotas get-service-quota --service-code sagemaker`.
