# Error Handling — OpenSearch Index Deployer
Error-handling deep dives and API error tables, moved verbatim from SKILL.md.

## Error handling
### Index creation fails with "mapper_parsing_exception"
- The mapping JSON has a syntax error or invalid field type. Validate
  the JSON and check field type names.

### Rollover fails with "illegal_argument_exception"
- The rollover alias does not have `"is_write_index": true`. Re-create
  the alias with the write index flag.

### k-NN search returns "index knn is disabled"
- The index was created without `"index.knn": true`. k-NN must be set
  at creation time. Create a new index and reindex.

### Force merge hangs or fails
- The index is still receiving writes. Block writes first
  (`"blocks": {"write": true}`), then force merge.

### Cluster goes red after creating a large index
- Not enough data nodes to allocate shards, or disk exceeded flood-stage
  watermark. Add nodes, increase disk, or reduce shard count. Check
  `GET _cat/allocation?v`.
