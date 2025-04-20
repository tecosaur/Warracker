-- 013_add_updated_at_to_tags.sql
-- Adds an updated_at column to the tags table for tracking updates

ALTER TABLE tags
ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
