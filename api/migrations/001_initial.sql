-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'host',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Podcasts table
CREATE TABLE IF NOT EXISTS podcasts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    language VARCHAR(10) DEFAULT 'en',
    target_languages TEXT[],
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Episodes table
CREATE TABLE IF NOT EXISTS episodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    podcast_id UUID NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    vision TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    current_version_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Versions table
CREATE TABLE IF NOT EXISTS versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    version_type VARCHAR(50) NOT NULL,
    content JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add foreign key from episodes to versions for current_version
ALTER TABLE episodes
    ADD CONSTRAINT fk_current_version
    FOREIGN KEY (current_version_id) REFERENCES versions(id)
    ON DELETE SET NULL;

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_podcasts_owner ON podcasts(owner_id);
CREATE INDEX idx_episodes_podcast ON episodes(podcast_id);
CREATE INDEX idx_versions_episode ON versions(episode_id);

-- Insert default admin user (password: admin123 — change in production!)
INSERT INTO users (email, name, hashed_password, role)
VALUES (
    'admin@podcast.local',
    'Admin User',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/I1i',
    'admin'
)
ON CONFLICT (email) DO NOTHING;
