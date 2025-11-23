CREATE TABLE demands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    scope_level INTEGER NOT NULL, -- 1 (hiper-local), 2 (serviço/região), 3 (cidade/estado)
    theme VARCHAR(50) NOT NULL,
    location JSONB, -- {address, coordinates, neighborhood, city, state}
    affected_entity VARCHAR(200), -- ex: "Linha 123 de ônibus", "UBS Vila Maria"
    urgency VARCHAR(20) NOT NULL,
    supporters_count INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE demand_supporters (
    demand_id UUID REFERENCES demands(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    supported_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (demand_id, user_id)
);

CREATE INDEX idx_demands_creator ON demands(creator_id);
CREATE INDEX idx_demands_scope_level ON demands(scope_level);
CREATE INDEX idx_demands_theme ON demands(theme);
CREATE INDEX idx_demands_status ON demands(status);
CREATE INDEX idx_demands_created_at ON demands(created_at DESC);

-- Adicionar FK em interactions
ALTER TABLE interactions 
ADD COLUMN demand_id UUID REFERENCES demands(id);

CREATE INDEX idx_interactions_demand_id ON interactions(demand_id);
