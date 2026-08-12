# Eval: rds-shared-cost

**Difficulty:** medium
**Branch:** FURTHER_OPTIMIZATION_AVAILABLE — 3 separate RDS db.t3.medium ($183/mo) → shared external db.t4g.medium with Graviton (~$57/mo)

## Prompt

Optimize RDS cost for three Elastic Beanstalk dev environments
(my-dev-app-1, my-dev-app-2, my-dev-app-3). Each has its own
db.t3.medium RDS instance attached to the environment
($61/mo each, total $183/mo). Recommend a shared external RDS
approach using Graviton (db.t4g.medium) with separate databases
per environment.
