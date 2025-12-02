-- Step 8: Add profile fields (bio, avatar_url, interests)
-- Execute manually in PostgreSQL after migration 007

-- Add new profile fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS bio TEXT,
ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512),
ADD COLUMN IF NOT EXISTS interests TEXT[];

-- Comments
COMMENT ON COLUMN users.bio IS 'User biography (max 300 characters)';
COMMENT ON COLUMN users.avatar_url IS 'Profile picture URL';
COMMENT ON COLUMN users.interests IS 'Array of user interests (e.g., Educação, Meio Ambiente)';
