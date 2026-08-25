# Error Handling — Lambda Layer Deployer

Failure modes for Lambda Layer publishing, attachment, imports, and
cross-account sharing. Moved verbatim from SKILL.md; load on demand.

### Error handling


### Layer attach fails (`ResourceConflictException`)

**Cause:** the layer's compatible runtimes or architectures do not
match the function's runtime or architecture.

**Fix:** verify the function's runtime and architecture via
`get-function-configuration`, then re-publish the layer with the
correct `--compatible-runtimes` and `--compatible-architectures`.

### Import fails at runtime (`ModuleNotFoundError`)

**Cause:** the layer zip structure does not match the runtime's
expected path.

**Fix:** verify the zip structure. For Python, dependencies must be
in `python/`. For Node.js, in `nodejs/node_modules/`. Re-zip from
inside the directory so the runtime path is at the zip root.

### Cross-account attach fails (`AccessDeniedException`)

**Cause:** either the resource-based policy is missing on the layer,
or the consuming role lacks `lambda:GetLayerVersion` permission.

**Fix:** verify both sides — `get-layer-version-policy` on the owner
side, and the consuming role's IAM policy. Both are required.

### Layer publish fails (`ResourceConflictException` on size)

**Cause:** the compressed zip exceeds 50 MB, or the total function
deployment size exceeds 250 MB.

**Fix:** reduce the layer size (remove unused dependencies, strip
debug symbols). If the dependency set is too large, switch to a
container image deployment.
