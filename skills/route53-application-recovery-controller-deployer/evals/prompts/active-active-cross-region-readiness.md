# Eval: active-active-cross-region-readiness

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — three-cell active-active with OR safety rule threshold 2, cross-region readiness, DynamoDB resource set

## Prompt

Create a Route 53 ARC setup for a three-region active-active
application. Cells: Cell-A in us-east-1, Cell-B in us-east-2,
Cell-C in us-west-2. Active-active topology. Recovery cluster
name global-app-cluster. Need at least two cells ON at all
times. Resource set for DynamoDB tables
(AWS::DynamoDB::Table) with one table per cell. Tags:
Environment=production, Topology=active-active-3cell.
