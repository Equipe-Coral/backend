-- Migration: Create interactions table
-- Description: Creates the interactions table to store chatbot conversation history

CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(50) NOT NULL,
    message_type VARCHAR(20) NOT NULL, -- 'text', 'audio', 'image'
    original_message TEXT,
    transcription TEXT,
    audio_duration_seconds FLOAT,
    classification VARCHAR(50), -- 'ONBOARDING', 'DEMANDA', 'DUVIDA', 'OUTRO'
    extracted_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_interactions_phone ON interactions(phone);
CREATE INDEX idx_interactions_message_type ON interactions(message_type);
CREATE INDEX idx_interactions_classification ON interactions(classification);
CREATE INDEX idx_interactions_created_at ON interactions(created_at DESC);
