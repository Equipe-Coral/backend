-- Step 2: Create conversation_states table
-- Execute manually in PostgreSQL

CREATE TABLE conversation_states (
    phone VARCHAR(50) PRIMARY KEY,
    current_stage VARCHAR(50) NOT NULL, -- 'new_user', 'onboarding_welcome', 'awaiting_location', 'confirming_location', 'onboarding_complete', 'processing_demand'
    context_data JSONB, -- temporary conversation data
    last_message_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for filtering by stage
CREATE INDEX idx_conversation_states_stage ON conversation_states(current_stage);
CREATE INDEX idx_conversation_states_last_message ON conversation_states(last_message_at);

-- Comment on columns
COMMENT ON COLUMN conversation_states.current_stage IS 'Current conversation state: new_user, awaiting_location, confirming_location, onboarding_complete, processing_demand';
COMMENT ON COLUMN conversation_states.context_data IS 'JSONB: temporary context data for the conversation';
