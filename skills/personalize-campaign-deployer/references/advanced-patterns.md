# Advanced Patterns — Personalize Campaign Deployer

Deep-dive material moved out of the SKILL.md body so the procedure
stays scannable. Loaded on demand by the skill.

## Mindset

**One-line takeaway:** Amazon Personalize takes interaction data
(user-item interactions), trains a recommendation model (solution
version) using a recipe (User-Personalization, SIMS, Popularity-
Counting), and serves it via a campaign with a minProvisionedTPS
that sets the cost floor. The User-Personalization recipe covers
roughly 90% of recommendation use cases. An event tracker enables
real-time recommendation updates via PutEvents without retraining.

Three misconceptions dominate Personalize misdesign at provisioning
time:

- **"minProvisionedTPS is just a performance setting."** It is not.
  `minProvisionedTPS` sets the COST FLOOR for the campaign. Personalize
  bills per-TPS-hour; setting minProvisionedTPS=10 when you need 1
  means you pay for 10 TPS 24/7. Start low (1) and scale up based on
  observed traffic; you can update minProvisionedTPS without deleting
  the campaign.

- **"Use SIMS or Popularity-Counting by default."** Wrong default.
  The User-Personalization recipe (aws-user-personalization) covers
  ~90% of use cases — it handles cold-start, real-time updates via
  event tracker, and produces personalized (not just popular)
  recommendations. SIMS is for item-to-item similarity ("customers who
  bought X also bought Y"). Popularity-Counting is a baseline, not a
  production recommendation.

- **"Retraining is automatic."** It is not, unless you configure
  AutoTraining. By default, a solution version is trained once on the
  snapshot of data at training time. To incorporate new interactions,
  you must either retrain manually (create a new solution version and
  update the campaign), enable AutoTraining (automatic retraining on
  a schedule), or use the event tracker for real-time updates without
  full retraining.

## Configuration dependency graph (novel heuristic)

Personalize configurations are NOT independent. The dataset group type
determines whether you use campaigns or recommenders. The recipe
determines the solution. The solution version creates the campaign.
Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Dataset group (CUSTOM or DOMAIN) | None (top-level) | DOMAIN groups use recommenders; CUSTOM uses solutions + campaigns | container for datasets |
| Dataset schema (Avro-like JSON) | Dataset group exists | IMMUTABLE after creation — cannot alter columns | typed columns for Interactions / Users / Items |
| Dataset (Interactions required) | Schema defined; dataset group exists | Interactions REQUIRED; Users/Items optional but recommended | the data store |
| Bulk import job | Dataset exists; S3 matches schema; IAM s3:GetObject | one-time; for updates use PutEvents or another import | trained model input |
| Solution (recipe) | Dataset group + Interactions dataset | recipe selection determines algorithm; cannot change after creation | algorithm blueprint |
| Solution version (training) | Solution exists; data imported | HPO takes longer but may improve metrics | trained model |
| Campaign | Solution version ACTIVE | minProvisionedTPS sets cost floor; can UPDATE without recreating | real-time GetRecommendations |
| Event tracker | Dataset group exists | ONE active tracker per group; recreating invalidates previous | real-time PutEvents updates |
| Filter | Dataset group exists | references dataset columns; validated at creation | filtered recommendations |
| Recommender (DOMAIN only) | DOMAIN dataset group exists | pre-built for ECOMMERCE / VIDEO / MUSIC | domain-optimized recs |
| Batch inference job | Solution version OR campaign exists; S3 I/O | writes JSON to S3; no real-time serving | offline scoring |

**The minProvisionedTPS row is the one a baseline model misses.** A
naive deployment sets minProvisionedTPS to a high default or does not
realize it sets the cost floor. The correct heuristic starts at 1 and
scales based on observed traffic. The procedure below forces an
explicit cost decision.

**Cross-dependency gotchas:**
- Schema is IMMUTABLE. To add columns, create a new schema + dataset
  and re-import.
- Event tracker is per dataset group. Only ONE active tracker per
  group; recreating invalidates the previous tracking ID.
- DOMAIN groups use recommenders; CUSTOM groups use the full solution
  → solution version → campaign flow. The two are not interchangeable.
- Campaign update (new solution version) takes effect within ~15
  minutes; the campaign is briefly in UPDATE_PENDING.

## Step 12 — Recent features


**Recent AWS features (2023-2026):**

- **AutoTraining GA (2023-2024):** Automatic retraining on a schedule
  (e.g., every 7 days). Eliminates manual solution-version creation
  for routine refreshes.

- **Domain recommenders expanded (2023-2024):** MUSIC domain added;
  ECOMMERCE and VIDEO recommenders enhanced with cold-start handling.

- **Trending recipes (2023-2024):** New recipes for trending items
  and time-decay popularity.

- **Increased dataset limits (2024-2025):** Maximum interactions per
  dataset raised; larger bulk import jobs supported.

- **Cold-start improvements (2024-2025):** User-Personalization recipe
  enhanced for better cold-start user and item handling.

- **Filter improvements (2024-2025):** Filter expressions support
  additional operators and contextual filtering.

- **Regional expansion (2024-2025):** Personalize available in
  additional regions (ap-southeast-3, eu-south-1).

- **Real-time event throughput (2024-2025):** PutEvents throughput
  increased; lower latency for real-time recommendation updates.

