# Baseline (no-skill) response: hybrid-mi-connection-lost-unmanaged

This hybrid-activated instance (`mi-hybridconnectionlostu`) has
`PingStatus: ConnectionLost` and the last ping was 9 days ago. The SSM
Agent has stopped checking in.

You should investigate whether the on-prem host is powered on, whether
the agent service is running, and whether it can reach the SSM service
endpoints over HTTPS.

Once the agent is reachable again, re-audit to confirm associations,
patches, and Session Manager are still healthy.
