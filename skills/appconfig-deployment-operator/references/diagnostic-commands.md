# Diagnostic Commands — AppConfig Deployment Operator

Live-account pre-flight command listings and diagnostic runbooks moved
verbatim from the SKILL.md body for progressive disclosure
(agentskills.io). Loaded on demand by the skill.

---

## Pre-flight: application / environment metadata gate

Run before classification. `list-applications` returns max 50/page
(`--max-results 50`, paginate with `--next-token`).

**Live-account pre-flight (skip if offline plan):**
1. `appconfig list-applications` — confirm application exists; capture `Id`.
2. `appconfig list-environments --application-id <app>` — confirm target environment; capture `Id` and `State`.
3. `appconfig list-configuration-profiles --application-id <app>` — confirm profile; capture `Id`, `Type`, `Validators`.
4. `appconfig get-hosted-configuration-version --application-id <app> --configuration-profile-id <profile> --version-number <v>` — read the configuration payload and validate against schema.
5. `appconfig list-deployment-strategies` — confirm strategy; capture `Id`, `GrowthFactor`, `DeploymentDurationInMinutes`, `BakeTimeInMinutes`, `ReplicaMultiplier`.
6. `appconfig list-deployments --application-id <app> --environment-id <env>` — check for an active `DEPLOYING` deployment.
7. `cloudwatch describe-alarms --alarm-names <names>` — verify every `MonitorList` alarm is `OK`.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `Environment.State: READY_FOR_DEPLOYMENT` | Required; any other state blocks start-deployment |
| `ConfigurationProfile.Type: AWS.AppConfig.FeatureFlags` | Requires a feature-flag schema Validators; JSON payload must match |
| `MonitorList[].AlarmArn` in `ALARM` | Deployment auto-rolls back; refuse to start |
| `Deployment.State: DEPLOYING` | Cannot start another; either wait or stop first |
| `HostedConfigurationVersion` size > 64 KB | Rejected by the service; split or move to S3-backed |

## Diagnostic flows

### Deployment stuck in `DEPLOYING`

1. `get-deployment` — capture `State`, `PercentageComplete`, `EventLog`.
2. If `PercentageComplete` is below 100 and `EventLog` shows recent
   step transitions, the deployment is healthy — wait for the next
   step boundary (`DeploymentDurationInMinutes + BakeTimeInMinutes`).
3. If `EventLog` shows no transitions for > 2 × step duration:
   - The deployment strategy `GrowthFactor` may be 0 (invalid) —
     new start-deployment with a valid strategy.
   - The configuration profile may have been deleted mid-deployment
     — `State` will transition to `TERMINATED`. Fix the profile and
     re-deploy.
4. If targets are not receiving the new version despite 100%
   completion, the runtime poll interval (Lambda extension 45s,
   agent 60s) introduces lag — wait one poll cycle.

### Deployment auto-rolled back (`ROLLING_BACK` / `ROLLED_BACK`)

1. `get-deployment` — read `EventLog` for the rollback trigger.
2. The trigger is always a `MonitorList` alarm transitioning to
   `ALARM` during a bake window. Identify the alarm.
3. `cloudwatch describe-alarms` — capture the alarm's metric,
   threshold, and current value.
4. Decide: fix the configuration and re-deploy, or widen the alarm
   threshold (only if the alarm was over-sensitive).
5. If `ROLLED_BACK` with no prior `COMPLETED` deployment, targets
   are at an unknown state — issue a new start-deployment with the
   known-good configuration version.

### Deployment `TERMINATED`

1. `get-deployment` — read `EventLog` for the termination reason.
2. Common causes:
   - Configuration profile deleted mid-deployment.
   - Configuration data validation failure (schema Validators
     rejected the payload).
   - IAM regression: caller lost `appconfig:GetConfiguration`.
3. Remediation: fix the cause (re-create profile, fix payload, fix
   IAM), then issue a fresh `start-deployment`. A terminated
   deployment cannot be resumed.
