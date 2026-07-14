-- Demo rows so the UI renders before opportunity-rank is live. Safe to delete.
-- expires_at NULL = never expires (so the demo always shows); created_at a recent epoch.
INSERT OR REPLACE INTO suggestion
 (id, tweet_id, tweet_url, tweet_text, author_handle, author_tier, score, factors, pillar, angle, drafts, rationale, status, created_at, expires_at)
VALUES
 ('demo-1','111','https://x.com/dankoe/status/111','most people dont need more time, they need fewer priorities','dankoe','A',0.87,
  '{"angle":0.9,"pillar":0.85,"author":0.8,"upside":0.7,"fresh":0.9}','leverage',
  'tie to your systems > goals thread — you have receipts',
  '["the trap is treating priorities as additive. every yes silently reprices every other yes.","did this for 2y — the unlock wasnt cutting tasks, it was refusing to start them"]',
  'high-authority author, on-pillar, early reply window','queued', 1784000000000, NULL),
 ('demo-2','222','https://x.com/thisiskp_/status/222','writing online is the highest-leverage skill of the decade','thisiskp_','A',0.74,
  '{"angle":0.75,"pillar":0.9,"author":0.8,"upside":0.5,"fresh":0.8}','audience-building',
  'agree + sharpen: compounding, not leverage, is the real mechanism',
  '["leverage undersells it. writing compounds — one post keeps paying out for years.","the sneaky part: it also compounds your thinking, not just your reach"]',
  'on-pillar, strong author, room in replies','queued', 1784000000000, NULL);
