# Eval: caching-and-parallelism

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — enable_caching with P30D window, ParallelismConfiguration=5, custom image pinned by digest/tag (cache key behavior noted)

## Prompt

Configure my SageMaker Pipeline named training-pipeline in
us-east-1. Enable caching with a 30-day cache window. Set
ParallelismConfiguration MaxParallelExecutionSteps=5. The
pipeline uses a custom algorithm image referenced by tag
my-registry/my-image:v1.4.2 (digest-pinned). Verify image pinning
is correct for cache behavior.
