# Eval: hierarchy-metric-aggregation

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — hierarchy defined in parent model, child assets associated, parent metric aggregates child measurements

## Prompt

Create a SiteWise asset hierarchy in us-east-1. Parent model
"Production Line" with metric property TotalOutput = SUM(PowerOutput,
300s) aggregated across child assets. Child model "Machine" with
measurement properties: PowerOutput (DOUBLE, kW), Temperature (DOUBLE,
C), Status (STRING). Hierarchy name "Contains Machines". Parent asset
"Line-A" with child assets "Machine-01" and "Machine-02". Account
123456789012. Tags: Facility=Factory1.
