# Baseline (without skill): spot-array-jobs-dependencies

The model partially addresses the request but:

1. Does not explain how to set up dual compute environment fallback (spot primary, on-demand secondary)
2. Job queue ordering does not explain that Batch tries CEs in order — spot first, on-demand only if spot unavailable
3. Array job specification misses the arrayProperties.size parameter
4. Does not explain how SEQUENTIAL dependency type works with array jobs
5. No mention of the dependsOn with jobId reference for cross-job dependencies
6. Missing spot fleet role ARN validation
