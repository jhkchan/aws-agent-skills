# Baseline (no-skill) response: sagemaker-projects-pipeline-not-triggered

This file captures what a generic assistant produces WITHOUT the
sagemaker-model-registry-operator skill loaded.

---

If your pipeline didn't trigger, you should check a few things:

1. Make sure the model package is actually approved.
2. Check that your EventBridge rule is set up correctly.
3. Look at the CodePipeline execution history.

You can also try triggering the pipeline manually with
`aws codepipeline start-pipeline-execution`. If that doesn't
work, you may need to contact AWS support.
