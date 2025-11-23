-- STEP 5: Tables for legislative items (PLs) and user interactions
-- API da Câmara dos Deputados integration

-- Table for storing legislative items (PLs, PECs, etc)
CREATE TABLE legislative_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT NOT NULL UNIQUE, -- ID from Câmara/Senado API
    source TEXT NOT NULL, -- 'camara', 'senado'
    type TEXT NOT NULL, -- 'PL', 'PEC', 'PLP', etc
    number TEXT NOT NULL,
    year INTEGER NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    ementa TEXT, -- Official full text
    status TEXT,
    last_update TIMESTAMP,
    themes JSONB, -- Identified themes
    keywords TEXT[], -- Keywords for search
    full_data JSONB, -- Complete API response for flexibility
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table for tracking user interactions with PLs
CREATE TABLE pl_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pl_id UUID NOT NULL REFERENCES legislative_items(id) ON DELETE CASCADE,
    interaction_type TEXT NOT NULL, -- 'view', 'support', 'comment'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_legislative_items_external_id ON legislative_items(external_id);
CREATE INDEX idx_legislative_items_source ON legislative_items(source);
CREATE INDEX idx_legislative_items_themes ON legislative_items USING gin(themes);
CREATE INDEX idx_legislative_items_keywords ON legislative_items USING gin(keywords);
CREATE INDEX idx_legislative_items_year ON legislative_items(year DESC);
CREATE INDEX idx_pl_interactions_user_id ON pl_interactions(user_id);
CREATE INDEX idx_pl_interactions_pl_id ON pl_interactions(pl_id);

-- Comments for documentation
COMMENT ON TABLE legislative_items IS 'Legislative items (PLs, PECs) from Câmara and Senado APIs';
COMMENT ON TABLE pl_interactions IS 'User interactions with legislative items (views, supports)';
COMMENT ON COLUMN legislative_items.external_id IS 'Unique ID from external API (Câmara/Senado)';
COMMENT ON COLUMN legislative_items.full_data IS 'Complete API response stored as JSONB for flexibility';
COMMENT ON COLUMN legislative_items.keywords IS 'Array of keywords for fast search with GIN index';
