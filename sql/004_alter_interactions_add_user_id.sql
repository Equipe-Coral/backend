-- Step 2: Add user_id foreign key to interactions table
-- Execute manually in PostgreSQL after creating users table

-- Add column
ALTER TABLE interactions 
ADD COLUMN user_id UUID REFERENCES users(id);

-- Create index
CREATE INDEX idx_interactions_user_id ON interactions(user_id);

-- Comment
COMMENT ON COLUMN interactions.user_id IS 'Foreign key to users table';
