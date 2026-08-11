# Eval prompt: ses-configuration-set-event-publishing-and-ip-pool

Create a configuration set with CloudWatch + SNS event
destinations and a dedicated IP pool with automatic warmup. Walk
the pre-flight checks and emit the standard VERDICT block.

## Scenario

An operator wants a configuration set `transactional-cs` in
`us-east-1` that publishes events to CloudWatch and SNS, plus a
dedicated IP pool with warmup.

## Known facts

- **Domain identity:** `example.com` (verified, DKIM signing,
  MAIL FROM configured).
- **Configuration set name:** `transactional-cs`.
- **CloudWatch destination:** dimension `Campaign` from
  `EMAIL_HEADER`; events `SEND`, `DELIVERY`, `BOUNCE`,
  `COMPLAINT`, `OPEN`, `CLICK`.
- **SNS destination:** topic
  `arn:aws:sns:us-east-1:111122223333:ses-feedback` for
  `BOUNCE`, `COMPLAINT`.
- **Dedicated IP pool:** `transactional-pool` with 2 dedicated
  IPs (`10.0.0.1`, `10.0.0.2`), automatic warmup enabled.
- **Pool assignment:** pool assigned to the configuration set via
  `put-configuration-set-delivery-options`.

## Symptom

The operator needs the `create-configuration-set`, event
destination attachment, `create-dedicated-ip-pool`, warmup
enablement, and pool assignment CLI sequence.
