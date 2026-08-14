-- Add github_access_token column to users for persisting OAuth tokens
ALTER TABLE users
ADD COLUMN IF NOT EXISTS github_access_token VARCHAR(2000);

-- Optionally index if required for lookups (not added by default)
-- CREATE INDEX IF NOT EXISTS idx_users_github_id ON users (github_id);
