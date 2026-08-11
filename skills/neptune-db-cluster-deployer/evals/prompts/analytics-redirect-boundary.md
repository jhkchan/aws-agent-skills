# Eval: analytics-redirect-boundary

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — workload is analytical (PageRank, connected-components on a large graph); Neptune DB is the wrong service; redirect to Neptune Analytics (separate aws graph API)

## Prompt

I need to run PageRank and connected-components on a 500M-vertex
graph in AWS. Provision a Neptune cluster named "research-graph" in
us-east-1 with db.x2gdb.16xlarge instances for this. We want
Multi-AZ and snapshots. Account ID: 123456789012.
