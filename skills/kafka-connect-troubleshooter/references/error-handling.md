# Error handling — kafka-connect-troubleshooter

Data-quality short-circuit tables, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Data-quality short-circuits (moved from SKILL.md)

| Condition | Effect on diagnosis |
|---|---|
| `describe-connector` returns `Connector not found` | Wrong ARN or region; verify via `list-connectors`. |
| CloudWatch log group missing | Logging not configured; cannot diagnose task exceptions. NEED_MORE_INFO. |
| Connector still `CREATING` or `UPDATING` | Not a failure — wait for state transition. |
| `RUNNING` but throughput zero | Diagnose as SOURCE_LAG or SINK_DLQ. |
| `trace` empty but task FAILED | Logs are the only source; NEED_MORE_INFO if logs missing. |
