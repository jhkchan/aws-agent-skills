# Eval: safety-rule-design-and-or

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — strict active-standby with AND rule (prevent both ON) and OR rule (prevent all OFF)

## Prompt

Create ARC routing controls for a strict active-standby
application where both cells must NEVER be ON simultaneously
(data consistency requirement). Cell-A in us-east-1, Cell-B in
us-west-2. Cluster: strict-app-cluster. I need both a rule to
prevent total outage AND a rule to prevent both cells ON at the
same time. Tags: Application=strict-standby.
