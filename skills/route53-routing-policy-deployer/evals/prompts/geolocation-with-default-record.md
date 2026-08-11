# Eval: geolocation-with-default-record

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — geolocation with explicit default record

## Prompt

Build geolocation routing for "geo.example.com" in zone
Z5DABCDEFGHIJK. North America (NA) -> 10.10.0.10, Europe (EU) ->
10.20.0.20, default (everywhere else) -> 10.30.0.30. TTL 300s.
Include health checks on each target.
