-- 1. Niche count and user distribution
SELECT niche, COUNT(*) AS user_count
FROM users
GROUP BY niche
ORDER BY niche;
-- Expect: 3 rows (fitness, food, tech), each ~5+ (accumulated dev-DB rows included)

-- 2. Posts per user — every user should have >= 150
SELECT u.id, u.niche, COUNT(c.id) AS post_count
FROM users u
JOIN channels ch ON ch.user_id = u.id
JOIN content c ON c.channel_id = ch.id
GROUP BY u.id, u.niche
ORDER BY post_count ASC
LIMIT 10;
-- Expect: minimum post_count >= 150 (excluding the earlier 5-post smoke-test user, which you know about)

-- 3. Platforms and content_types actually used
SELECT DISTINCT ch.platform FROM channels ch ORDER BY 1;
SELECT DISTINCT c.content_type FROM content c ORDER BY 1;
-- Expect: platform values drawn from the 6 allowed; content_type from the 5 allowed

-- 4. Metrics stored, 3 snapshots per post
SELECT c.id, COUNT(m.id) AS snapshot_count
FROM content c
JOIN metrics m ON m.content_id = c.id
GROUP BY c.id
HAVING COUNT(m.id) != 3
LIMIT 10;
-- Expect: 0 rows returned. Any row here means a post doesn't have exactly 3 snapshots.

-- 5. Power-law shape check: engagement (likes) distribution should be heavily right-skewed —
-- median should be far below the mean, and the max should be a large multiple of the median
SELECT
  percentile_cont(0.5) WITHIN GROUP (ORDER BY likes) AS median_likes,
  AVG(likes) AS mean_likes,
  MAX(likes) AS max_likes
FROM metrics
WHERE likes IS NOT NULL;
-- Expect: mean_likes noticeably > median_likes, max_likes many multiples of median_likes.
-- A normal distribution would show mean ≈ median; this should not.

-- 6. Planted signal check — does the (niche, hook_type, topic_tag) match dramatically
--    outperform everything else, within the same niche?
SELECT
  u.niche,
  (c.hook_type = sig.hook_type AND c.topic_tags @> ARRAY[sig.topic_tag]) AS is_planted_match,
  AVG(m.likes) AS avg_likes,
  COUNT(*) AS n
FROM users u
JOIN channels ch ON ch.user_id = u.id
JOIN content c ON c.channel_id = ch.id
JOIN metrics m ON m.content_id = c.id
JOIN (VALUES
  ('fitness', 'story', 'transformation'),
  ('food', 'listicle', 'quick_recipes'),
  ('tech', 'bold_claim', 'product_review')
) AS sig(niche, hook_type, topic_tag) ON sig.niche = u.niche
GROUP BY u.niche, is_planted_match
ORDER BY u.niche, is_planted_match;
-- Expect: for each niche, avg_likes where is_planted_match=true should be roughly
-- 3x higher than where is_planted_match=false (matching the 3.0x multiplier from config.py)

-- 7. Time-boost check — Tue/Thu 7-9pm posts should outperform on average
SELECT
  (EXTRACT(DOW FROM c.posted_at) IN (2, 4) AND EXTRACT(HOUR FROM c.posted_at) BETWEEN 19 AND 20) AS is_boost_window,
  AVG(m.likes) AS avg_likes,
  COUNT(*) AS n
FROM content c
JOIN metrics m ON m.content_id = c.id
GROUP BY is_boost_window;
-- Expect: is_boost_window=true shows higher avg_likes than false, roughly ~1.4x
-- Note: Postgres EXTRACT(DOW) is 0=Sunday..6=Saturday, so Tue=2, Thu=4 here —
-- different indexing than Python's weekday() used in generator.py (Mon=0), same calendar days