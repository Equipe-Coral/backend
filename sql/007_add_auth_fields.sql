-- Step 7: Add authentication fields to users table and create verification_codes table
-- Execute manually in PostgreSQL after previous migrations

-- Add new fields to users table for authentication
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS name VARCHAR(255),
ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE,
ADD COLUMN IF NOT EXISTS cpf VARCHAR(11) UNIQUE,
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS uf VARCHAR(2),
ADD COLUMN IF NOT EXISTS city VARCHAR(100),
ADD COLUMN IF NOT EXISTS address VARCHAR(255),
ADD COLUMN IF NOT EXISTS number VARCHAR(20),
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_cpf ON users(cpf);
CREATE INDEX IF NOT EXISTS idx_users_is_verified ON users(is_verified);

-- Create verification_codes table
CREATE TABLE IF NOT EXISTS verification_codes (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_verification_codes_email ON verification_codes(email);
CREATE INDEX IF NOT EXISTS idx_verification_codes_expires_at ON verification_codes(expires_at);

-- Comments
COMMENT ON TABLE verification_codes IS 'Stores temporary verification codes sent via WhatsApp';
COMMENT ON COLUMN verification_codes.code IS '6-digit numeric code';
COMMENT ON COLUMN verification_codes.expires_at IS 'Code expires after 10 minutes';
COMMENT ON COLUMN users.is_verified IS 'Whether user has verified their account via WhatsApp code';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password';
