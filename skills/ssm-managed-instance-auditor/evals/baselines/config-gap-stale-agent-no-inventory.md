# Baseline (no-skill) response: config-gap-stale-agent-no-inventory

This instance (`i-0configgapstaleagentnoinv`) is healthy on the
coverage, patch, and session dimensions, but the SSM Agent is out of
date (`IsLatestVersion: false`) and there is no
`AWS-GatherSoftwareInventory` or `AWS-UpdateSSMAgent` association
configured.

You should create the auto-update association to keep the agent current,
and add an inventory association to collect software, network, and file
data for incident response.

These are operational gaps rather than active security exposures.
