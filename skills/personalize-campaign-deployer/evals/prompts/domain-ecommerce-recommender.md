# Eval: domain-ecommerce-recommender

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ECOMMERCE DOMAIN dataset group, aws-ecomm-recommended-for-you recommender, minRecommendationRequestsPerSecond=1 (not solution+campaign)

## Prompt

Build a Personalize recommendation system for an e-commerce site in
us-east-1. Use an ECOMMERCE DOMAIN dataset group named shop-recs.
Interactions at s3://training-data/interactions.csv. Use the
Recommended For You recommender recipe
(aws-ecomm-recommended-for-you) with
minRecommendationRequestsPerSecond=1. Role
arn:aws:iam::123456789012:role/PersonalizeServiceRole. Account
123456789012.
