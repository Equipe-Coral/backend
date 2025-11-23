-- Step 2: Create users table
-- Execute manually in PostgreSQL

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(50) UNIQUE NOT NULL,
    first_contact_date TIMESTAMP DEFAULT NOW(),
    location_primary JSONB, -- {address, coordinates, neighborhood, city, state}
    status VARCHAR(50) DEFAULT 'onboarding_incomplete',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_status ON users(status);

-- Comment on columns
COMMENT ON COLUMN users.location_primary IS 'JSONB: {neighborhood, city, state, coordinates: [lat, lng], formatted_address}';
COMMENT ON COLUMN users.status IS 'Values: onboarding_incomplete, active, inactive';
