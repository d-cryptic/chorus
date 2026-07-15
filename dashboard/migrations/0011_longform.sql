-- X Premium Plus allows a single post far past 280 chars. post_gen emits `longform` when an
-- idea has real depth but not separable beats (a thread would break one continuous argument).
-- Nullable: most ideas are a plain post and must stay one.
ALTER TABLE suggestion ADD COLUMN longform TEXT;
