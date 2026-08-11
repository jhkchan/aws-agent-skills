# Eval prompt: rum-application-signals-correlation-gap

Diagnose why Application Signals client/server correlation cannot
be enabled. Walk the pre-flight checks and emit the standard
VERDICT block (APPLICATION, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS, REMEDIATION).

## Scenario

An operator wants RUM to correlate client-side sessions with
server-side Application Signals for the `checkout-api` service.
The RUM app monitor `checkout-web-prod` exists. However,
`aws application-signals list-services` returns an empty list
(Application Signals not yet enabled on the server workload), and
`aws xray get-sampling-rules` shows the Default rule with
`FixedRate=0.0`.

## Known facts

- **App monitor:** `checkout-web-prod` exists in `us-east-1`.
- **Application Signals server state:** `list-services` returns
  empty — `checkout-api` not discovered.
- **X-Ray Default sampling rule:** `FixedRate=0.0` (0% sampling).
- **Operator intent:** enable client-side X-Ray tracing in RUM,
  but ALSO wants the server-side correlation.
- **Guest role / identity pool:** properly wired.

## Symptom

The operator wants to enable RUM with X-Ray tracing. Determine
whether the full client/server correlation is achievable today
and what is blocking it. Surface the gaps.
